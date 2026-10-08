"""Filtros da fila de conversas."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListConversationsQuery:
    area: str | None = None
    channel: str | None = None
    status: str | None = None
    search: str | None = None
    # -- fila do atendente humano (Sprint 4) ---------------------------------
    transferred_only: bool = False
    sort_by: str | None = None
    assigned_agent: str | None = None
    include_unassigned: bool = True
