"""Caso de uso central: ingestão de uma mensagem de canal.

Percorre os seis requisitos funcionais em uma única transação de conversa:

    RF001  normaliza o evento, venha de onde vier
    RF003  resolve a identidade e recupera (ou abre) o contexto
    RF002  classifica a intenção
    RF004  roteia para o fluxo e consulta os sistemas internos
    RF006  aplica a persona da Claro sobre a resposta
    RF005  avalia se o caso deve sair do bot

Este objeto não sabe o que é Redis, MongoDB, Groq ou HTTP: fala apenas com as
portas do domínio. É por isso que ele é testável sem subir nada.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ...domain.entities import Conversation, ConversationEvent, Message, Session, new_id
from ...domain.ports import (AuditLog, BackendSystems, ConversationRepository,
                             CustomerRepository, IntentClassifier, SessionRepository,
                             StudioConfigRepository)
from ...domain.services.handover_policy import HandoverPolicy
from ...domain.services.identity_service import IdentityService
from ...domain.services.intent_continuity import IntentContinuityService
from ...domain.services.persona_service import PersonaService
from ...domain.services.reply_composer import ReplyComposer
from ...domain.services.routing_service import Flow, RoutingService
from ...domain.value_objects import (Author, Channel, Consent, Intent, Priority,
                                     UNIDENTIFIED)


@dataclass(frozen=True)
class IngestCommand:
    channel: Channel
    text: str
    customer_id: str | None = None
    external_id: str | None = None
    consent: Consent = field(default_factory=Consent)


@dataclass
class IngestResult:
    conversation_id: str
    session_id: str
    customer_id: str
    reply: str
    intent: Intent
    channel: Channel
    flow: str
    persona_applied: str
    context_recovered: bool
    context_note: str | None
    handover_triggered: bool
    handover_reason: str | None
    services_consulted: list[str]
    turns: int


class IngestMessageUseCase:
    def __init__(
        self,
        sessions: SessionRepository,
        conversations: ConversationRepository,
        customers: CustomerRepository,
        studio: StudioConfigRepository,
        classifier: IntentClassifier,
        backends: BackendSystems,
        audit: AuditLog,
        handover_policy: HandoverPolicy,
        persona: PersonaService | None = None,
        composer: ReplyComposer | None = None,
        routing: RoutingService | None = None,
    ) -> None:
        self._sessions = sessions
        self._conversations = conversations
        self._customers = customers
        self._studio = studio
        self._classifier = classifier
        self._backends = backends
        self._audit = audit
        self._handover = handover_policy
        self._persona = persona or PersonaService()
        self._composer = composer or ReplyComposer()
        self._routing = routing or RoutingService()
        self._identity = IdentityService(sessions, customers)
        self._continuity = IntentContinuityService(handover_policy.confidence_threshold)

    async def execute(self, command: IngestCommand) -> IngestResult:
        # ---- RF003a: de quem é esta mensagem -----------------------------
        customer_id = await self._identity.resolve(
            command.channel, command.external_id, command.customer_id)

        if not command.consent.allows("atendimento"):
            raise PermissionError(
                "Consentimento ausente para a finalidade 'atendimento' neste canal.")

        customer = await self._customers.get(customer_id)

        # ---- RF003b: retomar contexto ou abrir sessão --------------------
        conversation, session, recovered, note = await self._resume_or_open(
            customer_id, command.channel, customer)

        # ---- RF001: normalizar o evento ----------------------------------
        inbound = ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.customer, text=command.text, consent=command.consent,
        )
        await self._persist(inbound)
        await self._audit.record("message.ingested", customer_id, {
            "channel": command.channel.value,
            "conversation_id": conversation.id,
            "consent_scope": list(command.consent.scope),
        })

        # ---- caso já com atendente humano --------------------------------
        # O bot não responde por cima de uma conversa que já é de um atendente:
        # a mensagem é registrada, a conversa sobe na fila e quem responde é a
        # pessoa. Continuar respondendo aqui seria falar por cima do colega.
        if conversation.with_human:
            return await self._deliver_to_agent(
                conversation, session, command, customer_id)

        # ---- RF002: classificar a intenção -------------------------------
        history = [m.text for m in await self._conversations.transcript(conversation.id)]
        classified = await self._classifier.classify(command.text, history=history)

        # Uma resposta como "pode prosseguir" não muda de assunto: dentro de uma
        # conversa em andamento, ela herda a intenção já firmada. Tratar cada
        # mensagem como se fosse a primeira é exatamente o que faz o cliente
        # sentir que precisa se repetir.
        intent = self._continuity.reconcile(
            classified, session.last_intent or conversation.intent)
        conversation.apply_intent(
            intent, governs_area=self._continuity.governs_business_area(intent))
        session.last_intent = intent
        failures = session.register_classification(classified.is_confident)

        # ---- RF004: rotear e consultar sistemas internos -----------------
        route = self._routing.route(intent)
        data: dict = {}
        current_plan = customer.plan.name if customer and customer.plan else None

        for service in route.services:
            data[service] = await self._backends.call(
                service, customer_id=customer_id, current_plan=current_plan)
            if service not in session.services_consulted:
                session.services_consulted.append(service)

        raw_reply = self._composer.compose(route.flow, intent, data, current_plan,
                                           text=command.text)

        # ---- RF006: aplicar a persona ------------------------------------
        config = await self._studio.get()
        reply = self._persona.apply(
            raw_reply, config, command.channel,
            customer_first_name=customer.first_name if customer else "",
            greet=(session.turns == 0 or recovered is False),
        )

        # ---- RF005: o caso deve sair do bot? -----------------------------
        # A avaliação usa a intenção *efetiva*, não a classificação crua: uma
        # mensagem que apenas herdou o assunto da conversa não é motivo para
        # escalar. O que escala é a incompreensão repetida — daí o contador.
        decision = self._handover.evaluate(
            intent, command.text, conversation, consecutive_failures=failures)
        if decision.should_handover or route.flow is Flow.handover:
            transcript = await self._conversations.transcript(conversation.id)
            reason = decision.reason or "Fluxo de atendimento humano acionado"
            conversation.request_handover(reason, session.services_consulted, len(transcript) + 1)
            await self._audit.record("handover.requested", customer_id,
                                     {"conversation_id": conversation.id, "reason": reason})

        # ---- persistir a resposta ----------------------------------------
        outbound = ConversationEvent(
            channel=command.channel, customer_id=customer_id,
            session_id=session.session_id, conversation_id=conversation.id,
            author=Author.bot, text=reply, consent=command.consent,
        )
        await self._persist(outbound)

        conversation.record_message(command.text, command.channel, from_customer=True)
        if not customer:
            conversation.customer_name = conversation.customer_name or "Cliente não identificado"
        session.turns += 1

        await self._conversations.save(conversation)
        await self._sessions.save(session)

        return IngestResult(
            conversation_id=conversation.id,
            session_id=session.session_id,
            customer_id=customer_id,
            reply=reply,
            intent=intent,
            channel=command.channel,
            flow=route.flow.value,
            persona_applied=self._persona.describe(config, command.channel),
            context_recovered=recovered,
            context_note=note,
            handover_triggered=conversation.handover.requested,
            handover_reason=conversation.handover.reason,
            services_consulted=list(session.services_consulted),
            turns=session.turns,
        )

    async def _deliver_to_agent(self, conversation, session, command,
                                customer_id: str) -> IngestResult:
        """Encaminha a mensagem ao atendente que assumiu a conversa."""
        config = await self._studio.get()
        customer = await self._customers.get(customer_id)

        holding = self._persona.apply(
            "Sua mensagem foi encaminhada ao atendente que está com o seu caso. "
            "Ele responde em instantes.",
            config, command.channel,
            customer_first_name=customer.first_name if customer else "",
        )

        conversation.record_message(command.text, command.channel, from_customer=True)
        conversation.priority = Priority.high
        await self._conversations.save(conversation)
        await self._sessions.save(session)
        await self._audit.record("message.routed_to_agent", customer_id,
                                 {"conversation_id": conversation.id})

        return IngestResult(
            conversation_id=conversation.id, session_id=session.session_id,
            customer_id=customer_id, reply=holding,
            intent=conversation.intent or UNIDENTIFIED, channel=command.channel,
            flow="atendimento_humano",
            persona_applied=self._persona.describe(config, command.channel),
            context_recovered=True,
            context_note="Mensagem entregue ao atendente responsável pelo caso",
            handover_triggered=True,
            handover_reason=conversation.handover.reason,
            services_consulted=list(session.services_consulted),
            turns=session.turns,
        )

    # ------------------------------------------------------------------ RF003
    async def _resume_or_open(self, customer_id: str, channel: Channel, customer):
        """Retomar significa: já existe conversa aberta deste cliente. Se ela veio
        de outro canal, esta é exatamente a continuidade que a solução promete."""
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

    async def _persist(self, event: ConversationEvent) -> None:
        await self._conversations.add_message(Message(
            conversation_id=event.conversation_id, author=event.author,
            text=event.text, channel=event.channel, timestamp=event.occurred_at,
            intent=event.metadata.get("intent"),
        ))
