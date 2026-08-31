"""Encerramento do atendimento pelo atendente humano.

O gatilho é outro — um clique no console, não uma despedida do cliente —, mas o
efeito precisa ser o mesmo: a conversa fecha e a pesquisa vai junto. Se só o
caminho do bot disparasse NPS, a operação mediria bem o atendimento automatizado
e cegamente o humano, que é justamente o mais caro.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...domain.entities.conversation import Conversation
from ...domain.entities.message import Message
from ...domain.ports.audit_log import AuditLog
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository
from ...domain.ports.session_repository import SessionRepository
from ...domain.ports.studio_config_repository import StudioConfigRepository
from ...domain.services.nps_service import NpsService
from ...domain.services.persona_service import PersonaService
from ...domain.value_objects.author import Author
from ...domain.value_objects.channel import Channel
from ...domain.value_objects.response_source import ResponseSource


@dataclass
class ClosedConversation:
    conversation: Conversation
    survey_sent: bool
    survey_message: str


class CloseConversationUseCase:
    def __init__(self, conversations: ConversationRepository,
                 sessions: SessionRepository, customers: CustomerRepository,
                 studio: StudioConfigRepository, audit: AuditLog,
                 nps: NpsService | None = None,
                 persona: PersonaService | None = None) -> None:
        self._conversations = conversations
        self._sessions = sessions
        self._customers = customers
        self._studio = studio
        self._audit = audit
        self._nps = nps or NpsService()
        self._persona = persona or PersonaService()

    async def execute(self, conversation_id: str, closed_by: str,
                      with_survey: bool = True) -> ClosedConversation | None:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            return None

        customer = await self._customers.get(conversation.customer_id)
        config = await self._studio.get()
        first_name = customer.first_name if customer else ""

        # A pesquisa sai pelo último canal que o cliente usou — perguntar pelo
        # WhatsApp quem acabou de ser atendido no app é pedir para não responder.
        channel = conversation.channels_used[-1] if conversation.channels_used else Channel.web

        conversation.close(closed_by=closed_by, with_survey=with_survey)

        message = ""
        if with_survey:
            message = self._persona.apply(
                self._nps.question(first_name), config, channel,
                customer_first_name=first_name)

            await self._conversations.add_message(Message(
                conversation_id=conversation.id, author=Author.bot,
                text=message, channel=channel, source=ResponseSource.template,
            ))

            conversation.record_message(message, channel, from_customer=False)

            if (session := await self._sessions.get(conversation.session_id)):
                session.open_survey()
                await self._sessions.save(session)

        await self._conversations.save(conversation)
        await self._audit.record("conversation.closed", conversation.customer_id, {
            "conversation_id": conversation.id, "closed_by": closed_by,
            "survey": "enviada" if with_survey else "dispensada",
        })

        return ClosedConversation(conversation, with_survey, message)
