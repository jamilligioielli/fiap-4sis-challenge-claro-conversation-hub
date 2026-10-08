"""Caso de uso: histórico de conversas de um cliente (linha do tempo).

Devolve as conversas mais recentes de um cliente dentro de uma janela de
meses, cada uma já classificada (tipo, situação, nota), e os indicadores do
período. O front-end não recalcula nada: recebe o que exibir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ...domain.entities.conversation import Conversation
from ...domain.ports.audit_log import AuditLog
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository
from ...domain.services.conversation_insights_service import (ConversationInsights,
                                                              ConversationInsightsService)
from ...domain.value_objects.clock import utcnow

DEFAULT_MONTHS = 6
DEFAULT_LIMIT = 6
DAYS_PER_MONTH = 30


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


@dataclass
class HistoryEntry:
    conversation: Conversation
    message_count: int


@dataclass
class ConversationHistory:
    customer_id: str
    months: int
    items: list[HistoryEntry] = field(default_factory=list)
    insights: ConversationInsights = field(default_factory=ConversationInsights)


class GetConversationHistoryUseCase:
    def __init__(self, conversations: ConversationRepository, customers: CustomerRepository,
                 audit: AuditLog, insights: ConversationInsightsService | None = None) -> None:
        self._conversations = conversations
        self._customers = customers
        self._audit = audit
        self._insights = insights or ConversationInsightsService()

    async def execute(self, customer_id: str, months: int = DEFAULT_MONTHS,
                      limit: int = DEFAULT_LIMIT) -> ConversationHistory | None:
        """`None` quando não há cliente nem conversa com esse identificador."""
        customer = await self._customers.get(customer_id)
        every = await self._conversations.list(customer_id=customer_id)
        if customer is None and not every:
            return None

        await self._audit.record("customer.history.viewed", customer_id, {"months": months})

        since = utcnow() - timedelta(days=months * DAYS_PER_MONTH)
        window = sorted((c for c in every if _aware(c.started_at) >= since),
                        key=lambda c: _aware(c.started_at), reverse=True)

        items = []
        for conversation in window[:limit]:
            transcript = await self._conversations.transcript(conversation.id)
            items.append(HistoryEntry(conversation, len(transcript)))

        return ConversationHistory(
            customer_id=customer_id, months=months, items=items,
            insights=self._insights.calculate_insights(window),
        )
