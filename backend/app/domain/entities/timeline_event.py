"""Evento na linha do tempo do relacionamento com o cliente."""
from __future__ import annotations

from pydantic import BaseModel


class TimelineEvent(BaseModel):
    date: str
    event: str
    type: str
