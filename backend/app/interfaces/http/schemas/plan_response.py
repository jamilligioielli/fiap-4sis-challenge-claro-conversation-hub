"""Plano contratado."""
from __future__ import annotations

from pydantic import BaseModel


class PlanResponse(BaseModel):
    name: str
    price: float
    data_gb: int
    used_gb: float
    usage_percent: int
    line: str
    due_day: int
    status: str
