"""Plano contratado pelo cliente."""
from __future__ import annotations

from pydantic import BaseModel


class Plan(BaseModel):
    name: str
    price: float
    data_gb: int
    used_gb: float = 0.0
    line: str = ""
    due_day: int = 10
    status: str = "Ativo"

    @property
    def usage_percent(self) -> int:
        return round(self.used_gb / self.data_gb * 100) if self.data_gb else 0
