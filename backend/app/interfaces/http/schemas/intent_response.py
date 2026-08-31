"""Intenção identificada, como a interface a consome."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ....domain.value_objects.area import Area


class IntentResponse(BaseModel):
    slug: str = Field(description="Identificador estável da intenção.")
    name: str = Field(description="Rótulo legível, como aparece no console.")
    confidence: float = Field(description="0.0 a 1.0.")
    confidence_label: str = Field(description="Alta, Média ou Baixa.")
    area: Area
    entities: dict = Field(default_factory=dict)
    engine: str = Field(description="Qual classificador respondeu.")
    reasoning: str | None = None
