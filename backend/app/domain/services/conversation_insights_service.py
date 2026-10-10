"""Leitura do histórico de conversas de um cliente.

A linha do tempo mostra *o que* aconteceu; os indicadores dizem *o que isso
significa* para quem vai atender agora: o cliente volta toda semana? Sempre
pelo mesmo assunto? Costuma sair satisfeito? Um atendente que sabe que é a
quarta vez em um mês que a pessoa fala de lentidão começa a conversa de outro
jeito.

Regras puras, sem I/O.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from ..entities.conversation import Conversation
from ..entities.nps_survey import DETRACTOR_MAX, PASSIVE_MAX
from ..value_objects.area import Area


class HistoryStatus(str, Enum):
    open = "open"                # ainda em curso
    resolved = "resolved"        # encerrada sem nota de insatisfação
    unresolved = "unresolved"    # encerrada com nota de detrator

    @property
    def label(self) -> str:
        return {"open": "Em andamento", "resolved": "Resolvida",
                "unresolved": "Encerrada com insatisfação"}[self.value]


# Tipo do atendimento para a linha do tempo. Deriva da área de negócio, que já
# é a classificação normalizada do hub — a intenção fina continua no item.
TYPE_BY_AREA: dict[Area, tuple[str, str]] = {
    Area.vendas: ("vendas", "Vendas"),
    Area.suporte: ("suporte", "Suporte"),
    Area.tecnico: ("suporte", "Suporte"),
    Area.financeiro: ("financeiro", "Financeiro"),
    Area.retencao: ("cancelamento", "Cancelamento"),
    Area.marketing: ("consulta", "Consulta"),
}

INFORMATIONAL_INTENTS = {"consulta_informacao"}


def history_status(conversation: Conversation) -> HistoryStatus:
    """Encerrada é a que tem `closed_at`. Sem nota, conta como resolvida: a
    maioria das pesquisas não é respondida, e silêncio não é reclamação."""
    if conversation.closed_at is None:
        return HistoryStatus.open
    nps = conversation.nps
    if nps is not None and nps.score is not None and nps.score <= DETRACTOR_MAX:
        return HistoryStatus.unresolved
    return HistoryStatus.resolved


def history_type(conversation: Conversation) -> tuple[str, str]:
    """(chave, rótulo) do tipo de atendimento."""
    if conversation.intent and conversation.intent.slug in INFORMATIONAL_INTENTS:
        return "consulta", "Consulta"
    return TYPE_BY_AREA.get(conversation.area, ("suporte", "Suporte"))


def nps_category(score: float | None) -> str | None:
    if score is None:
        return None
    if score <= DETRACTOR_MAX:
        return "detrator"
    if score <= PASSIVE_MAX:
        return "neutro"
    return "promotor"


@dataclass(frozen=True)
class ConversationInsights:
    total_conversations: int = 0
    average_frequency_days: float | None = None
    most_common_type: str | None = None
    most_common_type_label: str | None = None
    average_nps: float | None = None
    average_nps_category: str | None = None
    resolution_rate: float | None = None
    closed_conversations: int = 0


class ConversationInsightsService:
    def calculate_insights(self, conversations: Sequence[Conversation]) -> ConversationInsights:
        if not conversations:
            return ConversationInsights()

        ordered = sorted(conversations, key=lambda c: c.started_at)

        # Frequência: intervalo médio entre o início de conversas consecutivas.
        frequency = None
        if len(ordered) >= 2:
            span = (ordered[-1].started_at - ordered[0].started_at).total_seconds()
            frequency = round(span / 86400 / (len(ordered) - 1), 1)

        types = Counter(history_type(c) for c in ordered)
        (common_key, common_label), _ = types.most_common(1)[0]

        scores = [c.nps.score for c in ordered
                  if c.nps is not None and c.nps.score is not None]
        average_nps = round(sum(scores) / len(scores), 1) if scores else None

        closed = [c for c in ordered if c.closed_at is not None]
        resolved = [c for c in closed if history_status(c) is HistoryStatus.resolved]
        resolution = round(len(resolved) / len(closed) * 100, 1) if closed else None

        return ConversationInsights(
            total_conversations=len(ordered),
            average_frequency_days=frequency,
            most_common_type=common_key,
            most_common_type_label=common_label,
            average_nps=average_nps,
            average_nps_category=nps_category(average_nps),
            resolution_rate=resolution,
            closed_conversations=len(closed),
        )
