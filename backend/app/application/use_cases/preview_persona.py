"""Pré-visualização do efeito da persona sobre uma mensagem.

Torna visível o que normalmente só se percebe conversando: mudar a formalidade
ou os emojis no Design Studio muda a fala em todos os canais ao mesmo tempo.
"""
from __future__ import annotations

from dataclasses import dataclass

from ...domain.ports.customer_repository import CustomerRepository
from ...domain.ports.studio_config_repository import StudioConfigRepository
from ...domain.services.persona_service import PersonaService
from ...domain.value_objects.channel import Channel

STUDIO_TO_CHANNEL = {
    "whatsapp": Channel.whatsapp,
    "webchat": Channel.web,
    "app": Channel.app,
    "voice": Channel.voice,
}


@dataclass
class ChannelPreview:
    channel_id: str
    channel_name: str
    formality_label: str
    use_emoji: bool
    max_length: int
    rendered: str
    length: int


@dataclass
class PersonaPreview:
    persona_name: str
    persona_version: int
    original: str
    previews: list[ChannelPreview]


class PreviewPersonaUseCase:
    def __init__(self, studio: StudioConfigRepository, customers: CustomerRepository,
                 persona: PersonaService | None = None) -> None:
        self._studio = studio
        self._customers = customers
        self._persona = persona or PersonaService()

    async def execute(self, message: str, channel_ids: list[str],
                      customer_id: str | None = None) -> PersonaPreview:
        config = await self._studio.get()

        first_name = ""
        if customer_id and (customer := await self._customers.get(customer_id)):
            first_name = customer.first_name

        previews: list[ChannelPreview] = []
        for studio_id in channel_ids:
            channel = STUDIO_TO_CHANNEL.get(studio_id)
            channel_config = config.channel(studio_id)
            if channel is None or channel_config is None:
                continue

            rendered = self._persona.apply(
                message, config, channel,
                customer_first_name=first_name, greet=True)

            previews.append(ChannelPreview(
                channel_id=studio_id,
                channel_name=channel_config.name,
                formality_label=channel_config.formality_label,
                use_emoji=channel_config.useEmoji,
                max_length=channel_config.maxLength,
                rendered=rendered,
                length=len(rendered),
            ))

        return PersonaPreview(
            persona_name=config.persona.name,
            persona_version=config.version,
            original=message,
            previews=previews,
        )
