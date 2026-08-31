"""Mensagem persistida de uma conversa."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..value_objects.author import Author
from ..value_objects.channel import Channel
from ..value_objects.clock import utcnow
from ..value_objects.intent import Intent
from ..value_objects.response_source import ResponseSource
from .identifiers import new_id


class Message(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    conversation_id: str
    author: Author
    text: str
    channel: Channel | None = None
    timestamp: datetime = Field(default_factory=utcnow)
    intent: Intent | None = None
    source: ResponseSource | None = Field(
        default=None,
        description="Preenchido em mensagens do assistente: quem redigiu o texto.",
    )
