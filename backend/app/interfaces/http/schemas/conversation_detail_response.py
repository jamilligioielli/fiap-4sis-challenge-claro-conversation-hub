"""Conversa completa."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ....domain.value_objects.area import Area
from ....domain.value_objects.channel import Channel
from ....domain.value_objects.conversation_status import ConversationStatus
from ....domain.value_objects.priority import Priority
from ....domain.value_objects.sentiment import Sentiment
from .ai_panel_response import AIPanelResponse
from .message_response import MessageResponse


class ConversationDetailResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    status: ConversationStatus
    area: Area
    priority: Priority
    channels_used: list[Channel]
    started_at: datetime
    initiated_by_company: bool = False
    sentiment: Sentiment | None = None
    sentiment_score: float | None = None
    attended_by: str = "bot"
    messages: list[MessageResponse]
    ai: AIPanelResponse
