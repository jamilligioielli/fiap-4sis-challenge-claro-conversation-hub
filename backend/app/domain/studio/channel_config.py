"""Configuração de tom de voz de um canal."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .channel_presentation import ChannelPresentation
from .voice_config import VoiceConfig


class ChannelConfig(BaseModel):
    id: str
    name: str
    formalityLevel: int = Field(default=50, ge=0, le=100)
    greeting: str = ""
    maxLength: int = 280
    useEmoji: bool = False
    guidelines: list[str] = Field(default_factory=list)
    sampleMessage: str = ""
    presentation: ChannelPresentation = Field(default_factory=ChannelPresentation)
    voiceConfig: VoiceConfig | None = None

    @property
    def formality_label(self) -> str:
        v = self.formalityLevel
        if v < 25:
            return "Muito Informal"
        if v < 45:
            return "Informal"
        if v < 60:
            return "Equilibrado"
        return "Formal" if v < 80 else "Muito Formal"
