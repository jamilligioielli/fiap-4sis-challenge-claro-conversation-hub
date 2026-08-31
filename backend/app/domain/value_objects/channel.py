"""Canal de origem de uma interação."""
from __future__ import annotations

from enum import Enum


class Channel(str, Enum):
    """Acrescentar um canal aqui e escrever o seu adaptador basta — o núcleo
    conversacional não muda."""

    whatsapp = "whatsapp"
    web = "web"
    app = "app"
    voice = "voice"

    @property
    def label(self) -> str:
        return {
            "whatsapp": "WhatsApp",
            "web": "Web Chat",
            "app": "App Claro",
            "voice": "Voz (URA)",
        }[self.value]

    @property
    def studio_id(self) -> str:
        """Identificador correspondente na configuração do Design Studio."""
        return {
            "whatsapp": "whatsapp",
            "web": "webchat",
            "app": "app",
            "voice": "voice",
        }[self.value]

    @property
    def simulatable(self) -> bool:
        """A URA é um canal de voz por ligação telefônica. Simular por texto
        daria uma impressão falsa do que o canal é."""
        return self is not Channel.voice
