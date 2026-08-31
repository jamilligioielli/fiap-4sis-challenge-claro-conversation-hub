"""Métricas operacionais."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .kpi_response import KPIResponse


class DashboardResponse(BaseModel):
    """Números crus. A formatação de exibição é responsabilidade da interface."""

    area: str
    has_data: bool = Field(
        description="Falso enquanto nenhuma conversa foi processada. O painel começa "
                    "vazio de propósito: os números vêm do uso, não de sementes.")
    conversations: KPIResponse
    resolution_rate: KPIResponse
    handover_rate: KPIResponse
    nps: KPIResponse
    week: list[dict]
    channels: list[dict]
    area_counts: dict[str, int]
    journey_breaks: list[dict]
    automation_opportunities: list[dict]
    alerts: list[dict]
    intents: list[dict]
