"""Processamento de uma mensagem vinda de um canal.

Percorre, em uma única transação de conversa: normalização do evento, resolução
de identidade, recuperação de contexto, classificação da intenção, roteamento
para o fluxo de negócio, consulta aos sistemas internos, redação da resposta e
avaliação de transbordo.

Este objeto não sabe o que é cache, banco, modelo de linguagem ou HTTP: fala
apenas com as portas do domínio.
"""
from __future__ import annotations

from ...domain.entities.conversation import Conversation
from ...domain.entities.conversation_event import ConversationEvent
from ...domain.entities.identifiers import new_id
from ...domain.entities.message import Message
from ...domain.entities.session import Session
from ...domain.ports.audit_log import AuditLog
from ...domain.ports.backend_systems import BackendSystems
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository
from ...domain.ports.intent_classifier import IntentClassifier
from ...domain.ports.response_generator import GenerationRequest, ResponseGenerator
from ...domain.ports.session_repository import SessionRepository
from ...domain.ports.studio_config_repository import StudioConfigRepository
from ...domain.services.closure_service import ClosureService
from ...domain.services.context_confirmation import ContextConfirmationService
from ...domain.services.handover_policy import HandoverPolicy
from ...domain.services.identity_service import IdentityService
from ...domain.services.intent_continuity import IntentContinuityService
from ...domain.services.nps_service import NpsService
from ...domain.services.persona_service import PersonaService
from ...domain.services.routing_service import Flow, RoutingService
from ...domain.value_objects.author import Author
from ...domain.value_objects.channel import Channel
from ...domain.value_objects.context_decision import ContextDecision
from ...domain.value_objects.priority import Priority
from ...domain.value_objects.response_source import ResponseSource
from ...domain.value_objects.unidentified_intent import UNIDENTIFIED
from ..dto.ingest_command import IngestCommand
from ..dto.ingest_result import IngestResult

# O que cada fluxo de negócio precisa que a resposta realize. É a instrução que
# orienta o redator generativo — sem ela o modelo escreve bonito e não resolve.
DIRECTIVES: dict[Flow, str] = {
    Flow.venda: ("Ajudar o cliente a escolher e confirmar a mudança de plano. Se ele já "
                 "indicou o plano desejado e confirmou, registre a alteração e diga quando "
                 "passa a valer. Se ainda não escolheu, apresente no máximo duas opções "
                 "com preço."),
    Flow.financeiro: ("Informar a situação da fatura com os dados apurados e oferecer o "
                      "envio da segunda via."),
    Flow.suporte: ("Informar o resultado do diagnóstico e propor o próximo passo prático. "
                   "Não peça para o cliente refazer teste que o sistema já fez."),
    Flow.retencao: ("Entender o motivo da insatisfação antes de qualquer oferta. Não "
                    "tente segurar o cliente com desconto na primeira frase."),
    Flow.informacao: "Responder a dúvida com os dados apurados, de forma direta.",
    Flow.handover: ("Avisar que vai transferir para um atendente humano e tranquilizar: o "
                    "histórico vai junto, o cliente não precisa repetir nada."),
    Flow.fallback: ("Você não entendeu o pedido. Peça um esclarecimento curto, sugerindo "
                    "os assuntos que você resolve, sem parecer um menu."),
}

# Quantas falas recentes do assistente contam para a checagem de repetição.
RECENT_TURNS = 3

# Usadas quando a resposta composta sairia idêntica a uma recente — ver
# `_avoid_repeating`. Retomam o assunto sem recitar o que já foi dito.
FOLLOW_UPS: dict[Flow, str] = {
    Flow.venda: "Voltando ao seu plano: qual das opções que te mostrei faz mais sentido?",
    Flow.financeiro: "Sobre a sua fatura: quer que eu envie a segunda via agora?",
    Flow.suporte: "Sobre a sua conexão: o problema continua depois do que tentamos?",
    Flow.retencao: "Me conta o que mais está pesando na sua decisão, para eu tentar resolver.",
    Flow.informacao: "Quer que eu detalhe alguma das opções que citei?",
    Flow.handover: "Só um instante — o atendente já está com o seu histórico em mãos.",
    Flow.fallback: "Me diz com outras palavras o que você precisa, que eu te ajudo.",
}


class IngestMessageUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        conversations: ConversationRepository,
        customers: CustomerRepository,
        studio: StudioConfigRepository,
        classifier: IntentClassifier,
        generator: ResponseGenerator,
        backends: BackendSystems,
        audit: AuditLog,
        handover_policy: HandoverPolicy,
        persona: PersonaService | None = None,
        routing: RoutingService | None = None,
        continuity: IntentContinuityService | None = None,
        context_confirmation: ContextConfirmationService | None = None,
        nps: NpsService | None = None,
        closure: ClosureService | None = None,
    ) -> None:
        self._sessions = sessions
        self._conversations = conversations
        self._customers = customers
        self._studio = studio
        self._classifier = classifier
        self._generator = generator
        self._backends = backends
        self._audit = audit
        self._handover = handover_policy
        self._persona = persona or PersonaService()
        self._routing = routing or RoutingService()
        self._continuity = continuity or IntentContinuityService(
            handover_policy.confidence_threshold)
        self._context = context_confirmation or ContextConfirmationService()
        self._nps = nps or NpsService()
        self._closure = closure or ClosureService()
        self._identity = IdentityService(sessions, customers)

    # ===================================================================== fluxo
    async def execute(self, command: IngestCommand) -> IngestResult:
        customer_id = await self._identity.resolve(
            command.channel, command.external_id, command.customer_id)

        if not command.consent.allows("atendimento"):
            raise PermissionError(
                "Consentimento ausente para a finalidade 'atendimento' neste canal.")

        customer = await self._customers.get(customer_id)
        config = await self._studio.get()

        conversation, session, recovered, switch_note = await self._resume_or_open(
            customer_id, command.channel, customer)

        await self._persist(ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.customer, text=command.text, consent=command.consent,
        ))
        await self._audit.record("message.ingested", customer_id, {
            "channel": command.channel.value,
            "conversation_id": conversation.id,
            "consent_scope": list(command.consent.scope),
        })

        if customer is not None:
            customer.last_inbound_at = conversation.updated_at
            await self._customers.save(customer)

        # -- pesquisa em aberto: a próxima mensagem é a nota -----------------
        if conversation.awaiting_nps:
            return await self._collect_nps(conversation, session, command,
                                           customer, customer_id, config)

        # -- a conversa já é de um atendente humano --------------------------
        if conversation.with_human:
            return await self._deliver_to_agent(conversation, session, command,
                                                customer, customer_id, config)

        # -- o cliente está se despedindo ------------------------------------
        if self._closure.wants_to_end(command.text):
            return await self._close_and_survey(conversation, session, command,
                                                customer, customer_id, config)

        # -- o cliente está respondendo à pergunta de continuidade -----------
        if session.awaiting_context_confirmation:
            handled = await self._resolve_context_question(
                conversation, session, command, customer, customer_id, config)
            if handled is not None:
                return handled
            # decisão tomada: segue o processamento normal abaixo
            conversation = await self._conversations.get(conversation.id) or conversation
            session = await self._sessions.get(session.session_id) or session

        # -- trocou de canal com assunto em aberto: perguntar antes de agir ---
        if switch_note and conversation.intent is not None:
            return await self._ask_context_question(
                conversation, session, command, customer, customer_id, config, switch_note)

        return await self._answer(conversation, session, command, customer,
                                  customer_id, config, recovered, switch_note)

    # ================================================================ resposta
    async def _answer(self, conversation: Conversation, session: Session,
                      command: IngestCommand, customer, customer_id: str,
                      config, recovered: bool, note: str | None) -> IngestResult:
        history = await self._conversations.transcript(conversation.id)
        classified = await self._classifier.classify(
            command.text, history=[m.text for m in history])

        # Uma resposta como "pode prosseguir" não muda de assunto: dentro de uma
        # conversa em andamento, ela herda a intenção já firmada.
        intent = self._continuity.reconcile(
            classified, session.last_intent or conversation.intent)
        conversation.apply_intent(
            intent, governs_area=self._continuity.governs_business_area(intent))
        session.last_intent = intent
        failures = session.register_classification(classified.is_confident)

        route = self._routing.route(intent)
        facts: dict = {}
        current_plan = customer.plan.name if customer and customer.plan else None

        for service in route.services:
            facts[service] = await self._backends.call(
                service, customer_id=customer_id, current_plan=current_plan)
            if service not in session.services_consulted:
                session.services_consulted.append(service)

        facts["__flow__"] = route.flow
        generated = await self._generator.generate(GenerationRequest(
            channel=command.channel,
            intent=intent,
            config=config,
            customer=customer,
            business_facts=facts,
            transcript=[{"author": m.author.value, "text": m.text} for m in history],
            customer_message=command.text,
            directive=DIRECTIVES.get(route.flow, DIRECTIVES[Flow.fallback]),
        ))

        reply = self._persona.apply(
            generated.text, config, command.channel,
            customer_first_name=customer.first_name if customer else "",
            greet=False,
        )
        reply = self._avoid_repeating(reply, history, route.flow)

        decision = self._handover.evaluate(
            intent, command.text, conversation, consecutive_failures=failures)
        if decision.should_handover or route.flow is Flow.handover:
            reason = decision.reason or "Fluxo de atendimento humano acionado"
            conversation.request_handover(
                reason, session.services_consulted, len(history) + 1)
            await self._audit.record("handover.requested", customer_id,
                                     {"conversation_id": conversation.id, "reason": reason})

        await self._persist(ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.bot, text=reply, consent=command.consent,
        ), source=generated.source)

        conversation.record_message(command.text, command.channel, from_customer=True)
        if customer is None:
            conversation.customer_name = conversation.customer_name or "Cliente não identificado"
        session.turns += 1

        await self._conversations.save(conversation)
        await self._sessions.save(session)

        return self._result(conversation, session, command, config, reply, intent,
                            generated, route.flow.value, recovered, note)

    @staticmethod
    def _avoid_repeating(reply: str, history: list[Message], flow: Flow) -> str:
        """Impede que o assistente mande a mesma frase duas vezes seguidas.

        Repetir palavra por palavra é a versão conversacional de não ouvir o
        cliente — e acontece justamente nos momentos que mais importam aqui:
        quando ele confirma que quer continuar o assunto, os dados apurados são
        os mesmos e o redator determinístico recompõe o mesmo texto. Com um
        modelo de linguagem no lugar isso não ocorre, porque a conversa inteira
        vai no prompt; a regra existe para o modo sem chave.
        """
        recent = [m.text.strip() for m in reversed(history) if m.author is Author.bot]
        # Olhar só a última fala não basta: a pergunta de continuidade entra
        # entre a oferta e a retomada, e a repetição salta um turno.
        if reply.strip() not in recent[:RECENT_TURNS]:
            return reply
        return FOLLOW_UPS.get(flow, FOLLOW_UPS[Flow.fallback])

    # ================================================= pergunta de continuidade
    async def _ask_context_question(self, conversation: Conversation, session: Session,
                                    command: IngestCommand, customer, customer_id: str,
                                    config, note: str) -> IngestResult:
        """Reconhece a conversa anterior e devolve a decisão ao cliente.

        O atendimento não avança nesta rodada de propósito: presumir que o
        cliente quer continuar no mesmo assunto é decidir por ele.
        """
        previous = session.previous_channel()
        history = await self._conversations.transcript(conversation.id)

        generated = await self._generator.generate(GenerationRequest(
            channel=command.channel,
            intent=conversation.intent or UNIDENTIFIED,
            config=config,
            customer=customer,
            business_facts={"canal_anterior": previous.label if previous else "outro canal"},
            transcript=[{"author": m.author.value, "text": m.text} for m in history],
            customer_message=command.text,
            directive=(
                f"O cliente acabou de migrar de canal e havia uma conversa em aberto sobre "
                f"{conversation.subject}. Reconheça essa conversa citando o assunto e "
                f"pergunte se ele quer continuar nela ou tratar de outro assunto. "
                f"Não avance no atendimento nesta mensagem."
            ),
            fallback_text=self._context.fallback_question(
                previous.label if previous else "outro canal", conversation.subject),
        ))

        reply = self._persona.apply(
            generated.text, config, command.channel,
            customer_first_name=customer.first_name if customer else "")

        session.ask_context_confirmation(note)
        session.turns += 1

        await self._persist(ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.bot, text=reply, consent=command.consent,
        ), source=generated.source)

        conversation.record_message(command.text, command.channel, from_customer=True)
        await self._conversations.save(conversation)
        await self._sessions.save(session)
        await self._audit.record("context.confirmation.asked", customer_id,
                                 {"conversation_id": conversation.id, "note": note})

        return self._result(conversation, session, command, config, reply,
                            conversation.intent or UNIDENTIFIED, generated,
                            "confirmacao_de_contexto", True, note,
                            awaiting_confirmation=True)

    async def _resolve_context_question(self, conversation: Conversation, session: Session,
                                        command: IngestCommand, customer, customer_id: str,
                                        config) -> IngestResult | None:
        """Interpreta a resposta. Devolve `None` quando o processamento normal
        deve continuar nesta mesma rodada."""
        decision = self._context.interpret(command.text)

        if decision is ContextDecision.continue_previous:
            session.clear_context_confirmation()
            await self._sessions.save(session)
            await self._audit.record("context.confirmation.continued", customer_id,
                                     {"conversation_id": conversation.id})
            return None

        if decision is ContextDecision.start_new:
            conversation.close()
            await self._conversations.save(conversation)

            fresh_session = Session(
                session_id=new_id("ses"), conversation_id=new_id("conv"),
                customer_id=customer_id, channels_used=[command.channel],
            )
            fresh = Conversation(
                id=fresh_session.conversation_id, session_id=fresh_session.session_id,
                customer_id=customer_id,
                customer_name=customer.name if customer else "",
                channels_used=[command.channel],
            )
            await self._conversations.save(fresh)
            await self._sessions.save(fresh_session)
            await self._audit.record("context.confirmation.restarted", customer_id,
                                     {"previous": conversation.id, "new": fresh.id})

            return await self._answer(fresh, fresh_session, command, customer,
                                      customer_id, config, recovered=False, note=None)

        # resposta ambígua: repete a pergunta uma vez, sem avançar
        reply = self._persona.apply(
            "Só para eu não me perder: quer continuar no assunto anterior ou prefere "
            "tratar de outra coisa?",
            config, command.channel,
            customer_first_name=customer.first_name if customer else "")

        await self._persist(ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.bot, text=reply, consent=command.consent,
        ), source=ResponseSource.template)
        await self._sessions.save(session)

        from ...domain.ports.response_generator import GeneratedResponse
        return self._result(
            conversation, session, command, config, reply,
            conversation.intent or UNIDENTIFIED,
            GeneratedResponse(text=reply, source=ResponseSource.template),
            "confirmacao_de_contexto", True, None, awaiting_confirmation=True)

    # ============================================ encerramento e pesquisa NPS
    async def _close_and_survey(self, conversation: Conversation, session: Session,
                                command: IngestCommand, customer, customer_id: str,
                                config, closed_by: str = "bot") -> IngestResult:
        """Encerra o atendimento e abre a pesquisa na mesma mensagem.

        A pergunta sai junto da despedida de propósito: pesquisa que chega
        depois, fora do contexto, é a que ninguém responde.
        """
        from ...domain.ports.response_generator import GeneratedResponse

        first_name = customer.first_name if customer else ""
        conversation.close(closed_by=closed_by, with_survey=True)
        session.open_survey()

        reply = self._persona.apply(
            self._nps.question(first_name), config, command.channel,
            customer_first_name=first_name)

        await self._persist(ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.bot, text=reply, consent=command.consent,
        ), source=ResponseSource.template)

        conversation.record_message(command.text, command.channel, from_customer=True)
        await self._conversations.save(conversation)
        await self._sessions.save(session)
        await self._audit.record("conversation.closed", customer_id, {
            "conversation_id": conversation.id, "closed_by": closed_by,
            "survey": "enviada",
        })

        return self._result(
            conversation, session, command, config, reply,
            conversation.intent or UNIDENTIFIED,
            GeneratedResponse(text=reply, source=ResponseSource.template),
            "encerramento", False, None, awaiting_nps=True)

    async def _collect_nps(self, conversation: Conversation, session: Session,
                           command: IngestCommand, customer, customer_id: str,
                           config) -> IngestResult:
        """Lê a nota. Insiste no máximo uma vez, e desiste com elegância."""
        from ...domain.ports.response_generator import GeneratedResponse

        first_name = customer.first_name if customer else ""
        score = self._nps.interpret(command.text)

        if score is not None:
            conversation.record_nps(score, comment=command.text)
            session.close_survey()
            reply = self._nps.acknowledgement(score, first_name)
            await self._audit.record("nps.answered", customer_id, {
                "conversation_id": conversation.id, "score": score,
                "category": conversation.nps.category,
            })
        elif self._nps.declined(command.text) or conversation.nps.attempts >= 1:
            # Uma insistência basta. Duas viram cobrança, e o cliente já disse
            # o que tinha para dizer ao não responder.
            conversation.dismiss_nps()
            session.close_survey()
            reply = self._nps.farewell()
            await self._audit.record("nps.declined", customer_id,
                                     {"conversation_id": conversation.id})
        else:
            conversation.nps.attempts += 1
            reply = self._nps.retry()

        reply = self._persona.apply(reply, config, command.channel,
                                    customer_first_name=first_name)

        await self._persist(ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.bot, text=reply, consent=command.consent,
        ), source=ResponseSource.template)

        conversation.record_message(command.text, command.channel, from_customer=True)
        await self._conversations.save(conversation)
        await self._sessions.save(session)

        return self._result(
            conversation, session, command, config, reply,
            conversation.intent or UNIDENTIFIED,
            GeneratedResponse(text=reply, source=ResponseSource.template),
            "pesquisa_de_satisfacao", False, None,
            awaiting_nps=conversation.awaiting_nps)

    # ================================================== conversa com o humano
    async def _deliver_to_agent(self, conversation: Conversation, session: Session,
                                command: IngestCommand, customer, customer_id: str,
                                config) -> IngestResult:
        """Depois do transbordo o assistente cala.

        Ele não responde, não confirma recebimento, não diz "já já alguém te
        atende". Quem está com o caso é uma pessoa, e um robô comentando por
        cima é ruído para o cliente e para o atendente. A mensagem é registrada,
        a conversa sobe na fila, e o silêncio é a resposta certa.
        """
        from ...domain.ports.response_generator import GeneratedResponse

        conversation.record_message(command.text, command.channel, from_customer=True)
        conversation.priority = Priority.high
        await self._conversations.save(conversation)
        await self._sessions.save(session)
        await self._audit.record("message.routed_to_agent", customer_id,
                                 {"conversation_id": conversation.id})

        return self._result(
            conversation, session, command, config, "",
            conversation.intent or UNIDENTIFIED,
            GeneratedResponse(text="", source=ResponseSource.template),
            "atendimento_humano", True,
            "Mensagem entregue ao atendente responsável pelo caso")

    # ======================================================= contexto e sessão
    async def _resume_or_open(self, customer_id: str, channel: Channel, customer):
        existing = await self._conversations.open_for_customer(customer_id)

        if existing:
            session = await self._sessions.get(existing.session_id) or Session(
                session_id=existing.session_id,
                conversation_id=existing.id,
                customer_id=customer_id,
                channels_used=list(existing.channels_used),
            )
            previous = session.channels_used[-1] if session.channels_used else None
            switched = session.register_channel(channel)

            note = None
            if switched and previous:
                note = (f"Cliente migrou de {previous.label} para {channel.label} "
                        f"mantendo histórico completo")
                await self._persist(ConversationEvent(
                    channel=channel, customer_id=customer_id,
                    session_id=session.session_id, conversation_id=existing.id,
                    author=Author.system, text=note,
                ))
            return existing, session, True, note

        session = Session(
            session_id=new_id("ses"), conversation_id=new_id("conv"),
            customer_id=customer_id, channels_used=[channel],
        )
        conversation = Conversation(
            id=session.conversation_id, session_id=session.session_id,
            customer_id=customer_id,
            customer_name=customer.name if customer else "",
            channels_used=[channel],
        )
        return conversation, session, False, None

    async def _persist(self, event: ConversationEvent,
                       source: ResponseSource | None = None) -> None:
        await self._conversations.add_message(Message(
            conversation_id=event.conversation_id, author=event.author,
            text=event.text, channel=event.channel, timestamp=event.occurred_at,
            source=source,
        ))

    def _result(self, conversation: Conversation, session: Session,
                command: IngestCommand, config, reply: str, intent, generated,
                flow: str, recovered: bool, note: str | None,
                awaiting_confirmation: bool = False,
                awaiting_nps: bool = False) -> IngestResult:
        return IngestResult(
            conversation_id=conversation.id,
            session_id=session.session_id,
            customer_id=conversation.customer_id,
            reply=reply,
            intent=intent,
            channel=command.channel,
            flow=flow,
            persona_applied=self._persona.describe(config, command.channel),
            persona_version=config.version,
            response_source=generated.source,
            response_model=generated.model,
            context_recovered=recovered,
            context_note=note,
            handover_triggered=conversation.handover.requested,
            handover_reason=conversation.handover.reason,
            services_consulted=list(session.services_consulted),
            turns=session.turns,
            awaiting_context_confirmation=awaiting_confirmation
            or session.awaiting_context_confirmation,
            awaiting_nps=awaiting_nps or conversation.awaiting_nps,
            conversation_closed=conversation.closed_at is not None,
            nps_score=conversation.nps.score if conversation.nps else None,
        )
