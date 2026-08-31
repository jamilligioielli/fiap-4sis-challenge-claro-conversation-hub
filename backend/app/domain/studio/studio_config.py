"""Configuração completa da persona conversacional."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..value_objects.clock import utcnow
from .channel_config import ChannelConfig
from .configured_intent import ConfiguredIntent
from .guardrail import Guardrail
from .persona import Persona


class StudioConfig(BaseModel):
    """O que o Design Studio edita. Salvar aqui muda o comportamento de todos os
    canais na próxima mensagem, sem implantação."""

    persona: Persona = Field(default_factory=Persona)
    intents: list[ConfiguredIntent] = Field(default_factory=list)
    guardrails: list[Guardrail] = Field(default_factory=list)
    channels: list[ChannelConfig] = Field(default_factory=list)
    version: int = Field(
        default=1,
        description="Incrementa a cada alteração. Permite mostrar na conversa "
                    "qual versão da persona produziu cada resposta.",
    )
    updated_at: datetime = Field(default_factory=utcnow)

    def channel(self, studio_id: str) -> ChannelConfig | None:
        return next((c for c in self.channels if c.id == studio_id), None)
