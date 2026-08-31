"""Comando de disparo de contato ativo."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SendOutreachCommand:
    customer_id: str
    offer_id: str
    channel: str = "whatsapp"
    agent: str = "Console"
    custom_message: str | None = None
