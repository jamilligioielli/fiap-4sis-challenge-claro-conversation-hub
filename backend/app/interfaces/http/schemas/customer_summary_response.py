"""Cliente como aparece na lista de personas do simulador."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ....domain.value_objects.channel import Channel


class CustomerSummaryResponse(BaseModel):
    """O suficiente para escolher com quem simular, sem carregar o perfil inteiro."""

    id: str
    name: str
    segment: str
    persona_summary: str = Field(description="Como esta pessoa costuma se comportar.")
    preferred_channel: Channel
    plan_name: str | None = None
    plan_usage_percent: int | None = None
    churn_label: str = ""
    marketing_opt_in: bool = False
    conversation_count: int = 0
    open_conversation_id: str | None = Field(
        default=None, description="Conversa em andamento, se houver.")
