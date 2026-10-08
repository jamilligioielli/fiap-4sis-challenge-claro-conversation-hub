"""Resultado do processamento de uma mensagem."""
from __future__ import annotations

from dataclasses import dataclass, field

from ...domain.value_objects.channel import Channel
from ...domain.value_objects.intent import Intent
from ...domain.value_objects.response_source import ResponseSource
from ...domain.value_objects.sentiment import Sentiment


@dataclass
class IngestResult:
    conversation_id: str
    session_id: str
    customer_id: str
    reply: str
    intent: Intent
    channel: Channel
    flow: str
    persona_applied: str
    persona_version: int
    response_source: ResponseSource
    response_model: str | None
    context_recovered: bool
    context_note: str | None
    handover_triggered: bool
    handover_reason: str | None
    services_consulted: list[str] = field(default_factory=list)
    turns: int = 0
    awaiting_context_confirmation: bool = False
    awaiting_nps: bool = False
    conversation_closed: bool = False
    nps_score: int | None = None
    sentiment: Sentiment | None = None
    sentiment_score: float | None = None
