"""Configuracao da persona -- o que o Design Studio edita (RF006).

Este e o modelo de configuracao do dominio. Ele nao conhece Tailwind nem React:
os campos de apresentacao (`color`, `bgColor`, `iconColor`) sao metadados que a
interface consome, e por isso ficam isolados em ChannelPresentation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .value_objects import utcnow


class VoiceConfig(BaseModel):
    """Configuracao da URA. So o canal de voz possui.

    A existencia deste bloco e a evidencia pratica do RNF004: um canal de
    natureza completamente diferente dos demais foi acrescentado sem que o
    nucleo conversacional precisasse mudar.
    """
    speechRate: int = Field(default=50, ge=0, le=100)
    voiceGender: Literal["feminino", "masculino"] = "feminino"
    vocabularyLevel: int = Field(default=40, ge=0, le=100)
    captureMode: Literal["dtmf", "voice", "hybrid"] = "hybrid"
    menuPattern: Literal["option-key", "key-option"] = "option-key"
    maxMenuOptions: int = Field(default=5, ge=2, le=9)
    autoRepeatTimeout: int = Field(default=8, ge=0, le=30, description="segundos de silêncio")
    maxAttempts: int = Field(default=3, ge=1, le=5)
    silenceTimeout: int = Field(default=3000, ge=500, le=10000, description="milissegundos")
    transferTriggers: list[str] = Field(default_factory=list)
    queueMessage: str = ""
    scriptOpening: str = ""
    scriptMenu: str = ""
    scriptFarewell: str = ""
    pronunciationGlossary: list[dict] = Field(default_factory=list)


class ChannelPresentation(BaseModel):
    """Metadados puramente visuais, separados da regra de negocio."""
    color: str = ""
    bgColor: str = ""
    iconColor: str = ""


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


class Persona(BaseModel):
    name: str = "Clara"
    description: str = ""
    traits: list[str] = Field(default_factory=list)


class ConfiguredIntent(BaseModel):
    """Intencao mapeada no Studio. `examples` alimenta o prompt do classificador."""
    slug: str
    name: str
    confidence: str = "Alta"
    examples: str = ""


class Guardrail(BaseModel):
    rule: str
    category: str


class StudioConfig(BaseModel):
    persona: Persona = Field(default_factory=Persona)
    intents: list[ConfiguredIntent] = Field(default_factory=list)
    guardrails: list[Guardrail] = Field(default_factory=list)
    channels: list[ChannelConfig] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utcnow)

    def channel(self, studio_id: str) -> ChannelConfig | None:
        return next((c for c in self.channels if c.id == studio_id), None)
