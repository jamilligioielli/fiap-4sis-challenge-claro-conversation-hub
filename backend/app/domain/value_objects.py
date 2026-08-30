"""Objetos de valor do dominio.

Sao imutaveis, nao tem identidade e nao dependem de nada de fora do dominio --
nem de framework, nem de banco, nem de HTTP.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Channel(str, Enum):
    """Canal de origem da interacao. Acrescentar um canal aqui e escrever o seu
    adaptador -- o nucleo nao muda (RNF004)."""
    whatsapp = "whatsapp"
    web = "web"
    app = "app"
    voice = "voice"

    @property
    def label(self) -> str:
        return {"whatsapp": "WhatsApp", "web": "Web Chat",
                "app": "App Claro", "voice": "Voz (URA)"}[self.value]

    @property
    def studio_id(self) -> str:
        """Id correspondente na configuracao do Design Studio."""
        return {"whatsapp": "whatsapp", "web": "webchat",
                "app": "app", "voice": "voice"}[self.value]


class Area(str, Enum):
    suporte = "Suporte"
    vendas = "Vendas"
    financeiro = "Financeiro"
    marketing = "Marketing"
    retencao = "Retenção"
    tecnico = "Técnico"


class ConversationStatus(str, Enum):
    active = "active"
    waiting = "waiting"
    transferred = "transferred"
    pending = "pending"


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Author(str, Enum):
    customer = "customer"
    bot = "bot"
    agent = "agent"
    system = "system"


class IntentEngine(str, Enum):
    llm = "llm"
    rules = "rules"


class Consent(BaseModel):
    """Consentimento granular por canal (RNF003 / LGPD).

    Viaja dentro do proprio evento, e nao numa tabela a parte, para que nenhuma
    etapa do processamento consiga tratar o dado sem saber o que foi autorizado.
    """
    model_config = ConfigDict(frozen=True)

    granted: bool = True
    scope: tuple[str, ...] = ("atendimento",)
    captured_at: datetime = Field(default_factory=utcnow)

    def allows(self, purpose: str) -> bool:
        return self.granted and purpose in self.scope


class Intent(BaseModel):
    """Resultado da classificacao (RF002)."""
    model_config = ConfigDict(frozen=True)

    slug: str
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    area: Area
    entities: dict = Field(default_factory=dict)
    engine: IntentEngine = IntentEngine.rules
    reasoning: str | None = None

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.55

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 0.75:
            return "Alta"
        if self.confidence >= 0.5:
            return "Média"
        return "Baixa"


UNIDENTIFIED = Intent(
    slug="nao_identificada", name="Não Identificada",
    confidence=0.25, area=Area.suporte,
    reasoning="Nenhuma intenção da taxonomia correspondeu à mensagem.",
)
