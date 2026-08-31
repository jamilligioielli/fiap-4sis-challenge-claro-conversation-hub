"""Contato ativo: quando a Claro inicia a conversa.

O atendimento reativo espera o cliente falar. Aqui é o contrário — e isso muda a
natureza do problema. Ninguém pediu para receber a mensagem, então a política de
contato deixa de ser detalhe e passa a ser a regra principal: sem consentimento
para oferta não sai nada, e fora da janela de atendimento livre o texto precisa
sair por modelo previamente aprovado.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...domain.entities.conversation import Conversation
from ...domain.entities.identifiers import new_id
from ...domain.entities.message import Message
from ...domain.entities.session import Session
from ...domain.outreach.eligibility import EligibleCustomer
from ...domain.outreach.template_category import TemplateCategory
from ...domain.ports.audit_log import AuditLog
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository
from ...domain.ports.response_generator import (GeneratedResponse, GenerationRequest,
                                                ResponseGenerator)
from ...domain.ports.session_repository import SessionRepository
from ...domain.ports.studio_config_repository import StudioConfigRepository
from ...domain.services.outreach_eligibility import OutreachEligibilityService
from ...domain.services.persona_service import PersonaService
from ...domain.value_objects.area import Area
from ...domain.value_objects.author import Author
from ...domain.value_objects.channel import Channel
from ...domain.value_objects.intent import Intent
from ...domain.value_objects.intent_engine import IntentEngine
from ...domain.value_objects.response_source import ResponseSource
from ..dto.outreach_command import SendOutreachCommand

OFFER_INTENT = Intent(
    slug="oferta_ativa",
    name="Oferta Ativa",
    confidence=1.0,
    area=Area.vendas,
    engine=IntentEngine.rules,
    reasoning="Contato iniciado pela Claro a partir de critério de elegibilidade.",
)


class OutreachBlocked(PermissionError):
    """A política de contato impediu o envio."""


@dataclass
class OutreachResult:
    conversation_id: str
    customer_id: str
    message: str
    channel: str
    template_category: str
    used_template: bool
    response_source: ResponseSource


class ListEligibleCustomersUseCase:
    def __init__(self, customers: CustomerRepository,
                 eligibility: OutreachEligibilityService | None = None) -> None:
        self._customers = customers
        self._eligibility = eligibility or OutreachEligibilityService()

    async def execute(self, only_contactable: bool = False) -> list[EligibleCustomer]:
        evaluated = [self._eligibility.evaluate(c) for c in await self._customers.all()]
        if only_contactable:
            evaluated = [e for e in evaluated if e.can_contact]
        return sorted(evaluated, key=lambda e: e.score, reverse=True)


class SendOutreachUseCase:
    def __init__(self, customers: CustomerRepository, conversations: ConversationRepository,
                 sessions: SessionRepository, studio: StudioConfigRepository,
                 generator: ResponseGenerator, audit: AuditLog,
                 eligibility: OutreachEligibilityService | None = None,
                 persona: PersonaService | None = None) -> None:
        self._customers = customers
        self._conversations = conversations
        self._sessions = sessions
        self._studio = studio
        self._generator = generator
        self._audit = audit
        self._eligibility = eligibility or OutreachEligibilityService()
        self._persona = persona or PersonaService()

    async def execute(self, command: SendOutreachCommand) -> OutreachResult:
        customer = await self._customers.get(command.customer_id)
        if customer is None:
            raise LookupError("Cliente não encontrado.")

        evaluation = self._eligibility.evaluate(customer)
        if evaluation.blocks:
            raise OutreachBlocked(
                "; ".join(block.description for block in evaluation.blocks))

        offer = evaluation.suggested_offer
        channel = Channel(command.channel)
        config = await self._studio.get()

        # Fora da janela de atendimento livre, a abordagem só pode sair por um
        # modelo previamente aprovado — texto gerado na hora não é permitido.
        used_template = not evaluation.window_open
        generated = await self._compose(
            channel, config, customer, evaluation, offer, command, used_template)

        message = self._persona.apply(
            generated.text, config, channel,
            customer_first_name=customer.first_name)

        conversation, session = await self._open_conversation(customer, channel)
        await self._conversations.add_message(Message(
            conversation_id=conversation.id, author=Author.bot,
            text=message, channel=channel, intent=OFFER_INTENT,
            source=generated.source,
        ))
        conversation.apply_intent(OFFER_INTENT)
        conversation.record_message(message, channel, from_customer=False)
        await self._conversations.save(conversation)

        session.last_intent = OFFER_INTENT
        await self._sessions.save(session)

        await self._audit.record("outreach.sent", customer.id, {
            "conversation_id": conversation.id,
            "offer": offer.id if offer else None,
            "category": offer.category.value if offer else None,
            "used_template": used_template,
            "agent": command.agent,
        })

        return OutreachResult(
            conversation_id=conversation.id,
            customer_id=customer.id,
            message=message,
            channel=channel.value,
            template_category=(offer.category.value if offer
                               else TemplateCategory.utility.value),
            used_template=used_template,
            response_source=generated.source,
        )

    # ------------------------------------------------------------- redação
    async def _compose(self, channel: Channel, config, customer, evaluation,
                       offer, command: SendOutreachCommand,
                       used_template: bool) -> GeneratedResponse:
        if command.custom_message:
            return GeneratedResponse(text=command.custom_message,
                                     source=ResponseSource.template)

        if used_template:
            return GeneratedResponse(text=self._approved_template(customer, offer),
                                     source=ResponseSource.template)

        reasons = "\n".join(f"- {r.description}" for r in evaluation.reasons) or "—"
        offer_text = (f"{offer.title} — {offer.pitch}."
                      f"{' ' + offer.saving_hint if offer.saving_hint else ''}"
                      if offer else "—")
        try:
            return await self._generator.generate(GenerationRequest(
                channel=channel, intent=OFFER_INTENT, config=config, customer=customer,
                business_facts={"motivos": reasons, "oferta": offer_text},
                customer_message="",
                fallback_text=self._approved_template(customer, offer),
                directive=(
                    "A Claro está iniciando este contato. Apresente-se, explique em uma "
                    "frase por que está falando com este cliente especificamente, faça a "
                    "oferta e deixe claro que recusar não muda nada no plano atual."
                ),
            ))
        except Exception:  # noqa: BLE001
            return GeneratedResponse(text=self._approved_template(customer, offer),
                                     source=ResponseSource.template)

    @staticmethod
    def _approved_template(customer, offer) -> str:
        """Texto no formato de modelo aprovado: variáveis preenchidas, sem improviso."""
        if offer is None:
            return (f"Olá, {customer.first_name}! Aqui é a Claro. Passando para saber "
                    f"se está tudo certo com o seu plano.")

        price = f"{offer.price:.2f}".replace(".", ",")
        return (
            f"Olá, {customer.first_name}! Aqui é a Claro. Notamos que o seu consumo tem "
            f"ficado perto do limite do plano atual. O {offer.title} sai por R$ {price} "
            f"por mês e te dá mais franquia. Quer saber mais? Se preferir, é só ignorar "
            f"esta mensagem."
        )

    async def _open_conversation(self, customer, channel: Channel):
        existing = await self._conversations.open_for_customer(customer.id)
        if existing is not None:
            session = await self._sessions.get(existing.session_id) or Session(
                session_id=existing.session_id, conversation_id=existing.id,
                customer_id=customer.id, channels_used=list(existing.channels_used),
            )
            return existing, session

        session = Session(session_id=new_id("ses"), conversation_id=new_id("conv"),
                          customer_id=customer.id, channels_used=[channel])
        conversation = Conversation(
            id=session.conversation_id, session_id=session.session_id,
            customer_id=customer.id, customer_name=customer.name,
            channels_used=[channel], area=Area.vendas,
            initiated_by_company=True,
        )
        await self._conversations.save(conversation)
        await self._sessions.save(session)
        return conversation, session
