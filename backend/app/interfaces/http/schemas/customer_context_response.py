"""Visão consolidada do cliente."""
from __future__ import annotations

from pydantic import BaseModel

from ....domain.value_objects.channel import Channel
from .plan_response import PlanResponse


class CustomerContextResponse(BaseModel):
    id: str
    name: str
    document_masked: str
    birth_date: str
    customer_since: str
    segment: str
    email: str
    phone: str
    preferred_channel: Channel
    persona_summary: str = ""
    marketing_opt_in: bool = False
    plan: PlanResponse | None
    products: list[dict]
    timeline: list[dict]
    churn_risk: float
    churn_label: str
    churn_factors: list[dict]
    upgrade_options: list[dict]
    conversation_count: int
    channels_used: list[Channel]
