"""Item da fila de conversas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ....domain.value_objects.area import Area
from ....domain.value_objects.channel import Channel
from ....domain.value_objects.conversation_status import ConversationStatus
from ....domain.value_objects.priority import Priority
from ....domain.value_objects.sentiment import Sentiment


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
    nps_score: int | None = Field(
        default=None, description="Nota dada pelo cliente no fim do atendimento.")
    nps_category: str | None = Field(
        default=None, description="`promotor`, `neutro`, `detrator` ou `sem resposta`.")
    closed_by: str | None = Field(
        default=None, description="Quem encerrou: `bot` ou o nome do atendente.")
    # -- Sprint 4 ---------------------------------------------------------
    handover_requested_at: datetime | None = Field(
        default=None, description="Momento da transferência para atendimento humano.")
    assigned_agent: str | None = Field(
        default=None, description="Atendente que assumiu o caso. Nulo = fila sem dono.")
    waiting_seconds: int | None = Field(
        default=None, description="Segundos desde a transferência, no momento da resposta.")
    attended_by: str = Field(
        default="bot", description="`bot` ou `agent` — se houve atendimento humano.")
    sentiment: Sentiment | None = Field(
        default=None, description="Humor atual do cliente: positive, neutral ou negative.")
    sentiment_score: float | None = Field(
        default=None, description="Índice de humor de 0 (insatisfeito) a 1 (satisfeito).")
