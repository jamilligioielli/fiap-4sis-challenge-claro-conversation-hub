"""Histórico de conversas de um cliente, para a linha do tempo do console."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ....domain.value_objects.area import Area
from ....domain.value_objects.channel import Channel
from ....domain.value_objects.sentiment import Sentiment


class ConversationHistoryItem(BaseModel):
    id: str
    date: str = Field(description="Data de início (AAAA-MM-DD).")
    started_at: datetime
    closed_at: datetime | None = None
    type: str = Field(description="vendas, suporte, financeiro, cancelamento ou consulta.")
    type_label: str
    intent: str | None = Field(default=None, description="Intenção identificada, legível.")
    area: Area
    status: str = Field(description="open, resolved ou unresolved.")
    status_label: str
    resolved: bool
    nps_score: int | None = None
    nps_category: str | None = Field(
        default=None, description="promotor, neutro, detrator ou `sem resposta`.")
    attended_by: str = Field(description="bot ou agent.")
    channels_used: list[Channel]
    message_count: int
    sentiment: Sentiment | None = None
    current: bool = Field(description="Conversa ainda vigente do cliente.")


class ConversationInsightsResponse(BaseModel):
    total_conversations: int
    average_frequency_days: float | None = Field(
        description="Dias, em média, entre uma conversa e a seguinte.")
    most_common_type: str | None
    most_common_type_label: str | None
    average_nps: float | None
    average_nps_category: str | None
    resolution_rate: float | None = Field(
        description="% das conversas encerradas que terminaram sem nota de detrator.")
    closed_conversations: int


class ConversationHistoryResponse(BaseModel):
    customer_id: str
    months: int
    items: list[ConversationHistoryItem]
    insights: ConversationInsightsResponse
