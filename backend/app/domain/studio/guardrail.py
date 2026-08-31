"""Regra inviolável de conduta do assistente."""
from __future__ import annotations

from pydantic import BaseModel


class Guardrail(BaseModel):
    rule: str
    category: str
