"""Filtros da fila de conversas."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListConversationsQuery:
    area: str | None = None
    channel: str | None = None
    status: str | None = None
    search: str | None = None
