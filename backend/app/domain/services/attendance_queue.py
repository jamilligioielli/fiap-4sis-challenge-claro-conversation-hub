"""Fila do atendente humano: quem entra e em que ordem.

A fila omnichannel mostra tudo o que passa pelo hub — inclusive o que o
assistente está resolvendo sozinho. Para quem atende, isso é ruído: o que
interessa é o que foi transferido para um humano e ainda não foi atendido, na
ordem em que precisa ser atendido.

A regra de ordenação fica aqui, como função pura, e não só na consulta ao
banco: ela é testável sem infraestrutura e vale igual para memória e MongoDB.
"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from enum import Enum

from ..entities.conversation import Conversation
from ..value_objects.priority import Priority

PRIORITY_RANK: dict[Priority, int] = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}


class QueueSort(str, Enum):
    """Critérios de ordenação da fila do atendente."""

    priority = "priority"      # prioridade, e em empate quem espera há mais tempo
    wait_time = "wait_time"    # quem espera há mais tempo, e em empate a prioridade
    recent = "recent"          # atividade mais recente primeiro


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def waiting_seconds(conversation: Conversation, now: datetime) -> int | None:
    """Tempo desde a transferência. `None` se a conversa não foi transferida."""
    requested_at = conversation.handover.requested_at
    if not conversation.handover.requested or requested_at is None:
        return None
    return max(0, int((_aware(now) - _aware(requested_at)).total_seconds()))


class AttendanceQueue:
    def transferred(self, conversations: Iterable[Conversation], *,
                    agent: str | None = None,
                    include_unassigned: bool = True) -> list[Conversation]:
        """Conversas com um humano e ainda em curso.

        Com `agent`, fica só o que é dele — e, se `include_unassigned`, também o
        que ainda não tem dono, que é a fila de onde ele puxa o próximo caso.
        """
        result = [c for c in conversations
                  if c.with_human and c.handover.requested and c.closed_at is None]
        if agent:
            result = [c for c in result
                      if c.handover.assigned_agent == agent
                      or (include_unassigned and c.handover.assigned_agent is None)]
        return result

    def sort(self, conversations: Iterable[Conversation], sort_by: QueueSort,
             now: datetime) -> list[Conversation]:
        items = list(conversations)

        def wait(c: Conversation) -> int:
            return waiting_seconds(c, now) or 0

        if sort_by is QueueSort.recent:
            return sorted(items, key=lambda c: _aware(c.updated_at), reverse=True)
        if sort_by is QueueSort.wait_time:
            return sorted(items, key=lambda c: (-wait(c), PRIORITY_RANK[c.priority]))
        return sorted(items, key=lambda c: (PRIORITY_RANK[c.priority], -wait(c)))
