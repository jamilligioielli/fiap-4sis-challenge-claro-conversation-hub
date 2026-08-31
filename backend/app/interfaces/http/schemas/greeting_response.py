"""Saudação de abertura do assistente."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GreetingResponse(BaseModel):
    conversation_id: str
    session_id: str
    customer_id: str
    greeting: str = Field(description="Primeira fala do assistente, na voz da marca.")
    persona_applied: str
    persona_version: int
    response_source: str
    response_model: str | None = None
    resumed: bool = Field(
        description="Verdadeiro quando havia conversa em aberto e ela foi retomada.")
