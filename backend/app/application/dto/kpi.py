"""Indicador do painel operacional."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KPI:
    value: float
    trend: float = 0.0
    unit: str = ""
