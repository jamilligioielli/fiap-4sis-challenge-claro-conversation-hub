"""Relógio do domínio.

Isolado para que o tempo seja substituível em teste — regra que depende de
`datetime.now()` espalhado pelo código é regra que não se testa.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
