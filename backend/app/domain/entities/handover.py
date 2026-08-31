"""Pacote que atravessa a fronteira entre assistente e atendente humano."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Handover(BaseModel):
    requested: bool = False
    reason: str | None = None
    requested_at: datetime | None = None
    assigned_agent: str | None = None
    services_consulted: list[str] = Field(default_factory=list)
    transcript_size: int = 0
