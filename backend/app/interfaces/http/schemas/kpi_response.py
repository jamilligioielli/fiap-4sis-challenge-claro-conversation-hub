"""Indicador numérico do painel."""
from __future__ import annotations

from pydantic import BaseModel


class KPIResponse(BaseModel):
    value: float
    trend: float
    unit: str = ""
