"""Painel de apoio ao atendente."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .intent_response import IntentResponse


class AIPanelResponse(BaseModel):
    intent: IntentResponse | None = None
    summary: dict[str, str] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)
    insights: list[dict] = Field(default_factory=list)
    handover: dict = Field(default_factory=dict)
