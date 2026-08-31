"""Prioridade de atendimento na fila."""
from __future__ import annotations

from enum import Enum


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
