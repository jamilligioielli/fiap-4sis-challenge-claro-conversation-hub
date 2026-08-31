"""Intenção de negócio identificada numa mensagem."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .area import Area
from .intent_engine import IntentEngine


class Intent(BaseModel):
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
        return "Média" if self.confidence >= 0.5 else "Baixa"
