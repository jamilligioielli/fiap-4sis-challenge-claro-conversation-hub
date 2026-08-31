"""Evento conversacional — o formato único de entrada do hub."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..value_objects.author import Author
from ..value_objects.channel import Channel
from ..value_objects.clock import utcnow
from ..value_objects.consent import Consent
from .identifiers import new_id


class ConversationEvent(BaseModel):
    """Qualquer canal, ao entrar no hub, produz exatamente esta forma. Depois
    deste ponto o núcleo não sabe — nem precisa saber — de onde a mensagem veio."""

    event_id: str = Field(default_factory=lambda: new_id("evt"))
    occurred_at: datetime = Field(default_factory=utcnow)
    channel: Channel
    customer_id: str
    session_id: str
    conversation_id: str
    author: Author
    text: str
    consent: Consent = Field(default_factory=Consent)
    metadata: dict = Field(default_factory=dict)
