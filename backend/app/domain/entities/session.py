"""Contexto de curto prazo de uma conversa. Vive em cache, com tempo de vida."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..value_objects.channel import Channel
from ..value_objects.intent import Intent
from .identifiers import new_id


class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: new_id("ses"))
    conversation_id: str
    customer_id: str
    channels_used: list[Channel] = Field(default_factory=list)
    turns: int = 0
    services_consulted: list[str] = Field(default_factory=list)
    last_intent: Intent | None = None
    consecutive_low_confidence: int = 0

    awaiting_context_confirmation: bool = Field(
        default=False,
        description="O assistente perguntou se o cliente quer retomar o assunto "
                    "anterior e ainda não obteve resposta.",
    )
    pending_channel_switch: str | None = Field(
        default=None,
        description="Descrição da migração que motivou a pergunta de contexto.",
    )

    def register_channel(self, channel: Channel) -> bool:
        """Registra o canal e informa se houve troca em relação ao anterior."""
        switched = bool(self.channels_used) and self.channels_used[-1] != channel
        if channel not in self.channels_used:
            self.channels_used.append(channel)
        elif switched:
            self.channels_used.remove(channel)
            self.channels_used.append(channel)
        return switched

    def previous_channel(self) -> Channel | None:
        return self.channels_used[-2] if len(self.channels_used) > 1 else None

    def register_classification(self, confident: bool) -> int:
        """Conta quantas mensagens seguidas o hub não conseguiu entender.

        Uma mensagem sem sinal próprio dentro de um assunto já firmado é normal
        ("pode prosseguir"). Três seguidas já são um cliente sendo mal atendido.
        """
        self.consecutive_low_confidence = 0 if confident else self.consecutive_low_confidence + 1
        return self.consecutive_low_confidence

    def ask_context_confirmation(self, note: str) -> None:
        self.awaiting_context_confirmation = True
        self.pending_channel_switch = note

    def clear_context_confirmation(self) -> None:
        self.awaiting_context_confirmation = False
        self.pending_channel_switch = None
