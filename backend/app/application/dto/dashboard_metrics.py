"""Métricas operacionais derivadas das conversas processadas."""
from __future__ import annotations

from dataclasses import dataclass, field

from .kpi import KPI


@dataclass
class DashboardMetrics:
    area: str
    conversations: KPI
    resolution_rate: KPI
    handover_rate: KPI
    nps: KPI
    week: list[dict] = field(default_factory=list)
    channels: list[dict] = field(default_factory=list)
    area_counts: dict[str, int] = field(default_factory=dict)
    journey_breaks: list[dict] = field(default_factory=list)
    automation_opportunities: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    intents: list[dict] = field(default_factory=list)
    has_data: bool = False
