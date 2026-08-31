"""Item da fila de conversas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ....domain.value_objects.area import Area
from ....domain.value_objects.channel import Channel
from ....domain.value_objects.conversation_status import ConversationStatus
from ....domain.value_objects.priority import Priority


class ConversationListItem(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    channel: Channel = Field(description="Canal mais recente da conversa.")
    channels_used: list[Channel]
    status: ConversationStatus
    last_message: str
    timestamp: str = Field(description="Rótulo relativo pronto para exibição.")
    updated_at: datetime
    started_at: datetime
    priority: Priority
    area: Area
    unread: bool
    intent: str | None = None
    confidence: float | None = None
    handover_requested: bool = False
    initiated_by_company: bool = False
    message_count: int = 0
