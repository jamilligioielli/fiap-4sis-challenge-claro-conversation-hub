"""Mensagem de uma transcrição."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ....domain.value_objects.author import Author
from ....domain.value_objects.channel import Channel
from ....domain.value_objects.sentiment import Sentiment
from .intent_response import IntentResponse


class MessageResponse(BaseModel):
    id: str
    author: Author
    text: str
    channel: Channel | None = None
    timestamp: datetime
    intent: IntentResponse | None = None
    source: str | None = None
    sentiment: Sentiment | None = None
