"""Abertura de conversa com saudação do assistente.

Existe para que a primeira tela do cliente não seja um campo de texto vazio: é o
assistente quem cumprimenta e convida a falar, como faria qualquer atendimento
que se preze.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...domain.entities.conversation import Conversation
from ...domain.entities.conversation_event import ConversationEvent
from ...domain.entities.identifiers import new_id
from ...domain.entities.message import Message
from ...domain.entities.session import Session
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository
from ...domain.ports.response_generator import (GeneratedResponse, GenerationRequest,
                                                ResponseGenerator)
from ...domain.ports.session_repository import SessionRepository
from ...domain.ports.studio_config_repository import StudioConfigRepository
from ...domain.services.persona_service import PersonaService
from ...domain.value_objects.author import Author
from ...domain.value_objects.channel import Channel
from ...domain.value_objects.response_source import ResponseSource
from ...domain.value_objects.unidentified_intent import UNIDENTIFIED


@dataclass
class StartedConversation:
    conversation_id: str
    session_id: str
    customer_id: str
    greeting: str
    persona_applied: str
    persona_version: int
    response_source: ResponseSource
    response_model: str | None
    resumed: bool


class StartConversationUseCase:
    def __init__(self, sessions: SessionRepository, conversations: ConversationRepository,
                 customers: CustomerRepository, studio: StudioConfigRepository,
                 generator: ResponseGenerator,
                 persona: PersonaService | None = None) -> None:
        self._sessions = sessions
        self._conversations = conversations
        self._customers = customers
        self._studio = studio
        self._generator = generator
        self._persona = persona or PersonaService()

    async def execute(self, customer_id: str, channel: Channel) -> StartedConversation | None:
        customer = await self._customers.get(customer_id)
        if customer is None:
            return None

        config = await self._studio.get()
        existing = await self._conversations.open_for_customer(customer_id)

        if existing is not None:
            session = await self._sessions.get(existing.session_id) or Session(
                session_id=existing.session_id, conversation_id=existing.id,
                customer_id=customer_id, channels_used=list(existing.channels_used),
            )
            return StartedConversation(
                conversation_id=existing.id, session_id=session.session_id,
                customer_id=customer_id, greeting="",
                persona_applied=self._persona.describe(config, channel),
                persona_version=config.version,
                response_source=ResponseSource.template, response_model=None,
                resumed=True,
            )

        session = Session(session_id=new_id("ses"), conversation_id=new_id("conv"),
                          customer_id=customer_id, channels_used=[channel])
        conversation = Conversation(
            id=session.conversation_id, session_id=session.session_id,
            customer_id=customer_id, customer_name=customer.name,
            channels_used=[channel],
        )

        generated = await self._greet(channel, config, customer)
        greeting = self._persona.apply(
            generated.text, config, channel,
            customer_first_name=customer.first_name)

        await self._conversations.save(conversation)
        await self._sessions.save(session)
        await self._conversations.add_message(Message(
            conversation_id=conversation.id, author=Author.bot,
            text=greeting, channel=channel, source=generated.source,
        ))
        conversation.record_message(greeting, channel, from_customer=False)
        await self._conversations.save(conversation)

        return StartedConversation(
            conversation_id=conversation.id, session_id=session.session_id,
            customer_id=customer_id, greeting=greeting,
            persona_applied=self._persona.describe(config, channel),
            persona_version=config.version,
            response_source=generated.source, response_model=generated.model,
            resumed=False,
        )

    async def _greet(self, channel: Channel, config, customer) -> GeneratedResponse:
        fallback = self._plain_greeting(channel, config, customer)
        try:
            return await self._generator.generate(GenerationRequest(
                channel=channel, intent=UNIDENTIFIED, config=config, customer=customer,
                customer_message="", fallback_text=fallback,
                directive=("O cliente acabou de abrir a conversa e ainda não escreveu nada. "
                           "Cumprimente pelo primeiro nome e pergunte como pode ajudar. "
                           "Não ofereça menu e não invente pendência."),
            ))
        except Exception:  # noqa: BLE001
            return GeneratedResponse(text=fallback, source=ResponseSource.template)

    def _plain_greeting(self, channel: Channel, config, customer) -> str:
        """Saudação usada quando não há redator generativo disponível."""
        channel_config = config.channel(channel.studio_id)
        template = channel_config.greeting if channel_config else "Olá, {nome}!"
        greeting = self._persona.interpolate_greeting(template, customer.first_name)
        return (f"{greeting} Sou a {config.persona.name}, assistente virtual da Claro. "
                f"Como posso te ajudar hoje?")
