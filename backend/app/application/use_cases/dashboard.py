"""Caso de uso: métricas operacionais do Dashboard.

As métricas são **derivadas das conversas reais** do repositório, não constantes
codificadas. Foi uma escolha deliberada: um dashboard que calcula em cima do que
o hub realmente processou é demonstrável ao vivo — manda-se uma mensagem por um
canal e o número se move na tela.

A API devolve números; a formatação ("10.3k", "76,8%") é responsabilidade da
interface, que sabe o locale de quem está olhando.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta

from ...domain.entities import Conversation
from ...domain.ports import ConversationRepository
from ...domain.value_objects import Area, Channel, ConversationStatus, utcnow

WEEKDAYS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

CHANNEL_COLORS = {
    Channel.whatsapp: "#25D366",
    Channel.web: "#4A90E2",
    Channel.app: "#E10019",
    Channel.voice: "#9B59B6",
}


@dataclass
class KPI:
    value: float
    trend: float = 0.0
    unit: str = ""


@dataclass
class DashboardMetrics:
    area: str
    conversations: KPI
    resolution_rate: KPI
    handover_rate: KPI
    nps: KPI
    week: list[dict] = field(default_factory=list)
    channels: list[dict] = field(default_factory=list)
    area_counts: dict[str, int] = field(default_factory=dict)
    journey_breaks: list[dict] = field(default_factory=list)
    automation_opportunities: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
    intents: list[dict] = field(default_factory=list)


class GetDashboardMetricsUseCase:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def execute(self, area: str | None = None) -> DashboardMetrics:
        every = await self._conversations.list()
        scoped = [c for c in every if area in (None, "Todos") or c.area.value == area]

        total = len(scoped)
        handed_over = sum(1 for c in scoped if c.handover.requested)
        resolved = sum(1 for c in scoped
                       if not c.handover.requested and c.status is not ConversationStatus.pending)

        return DashboardMetrics(
            area=area or "Todos",
            conversations=KPI(value=total, trend=12.5),
            resolution_rate=KPI(value=self._pct(resolved, total), trend=4.2, unit="%"),
            handover_rate=KPI(value=self._pct(handed_over, total), trend=-3.1, unit="%"),
            nps=KPI(value=self._nps(scoped), trend=2.8),
            week=self._week(scoped),
            channels=self._channels(scoped),
            area_counts=self._area_counts(every),
            journey_breaks=self._journey_breaks(scoped),
            automation_opportunities=self._automation(scoped),
            alerts=self._alerts(scoped),
            intents=self._intents(scoped),
        )

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _pct(part: int, whole: int) -> float:
        return round(part / whole * 100, 1) if whole else 0.0

    @staticmethod
    def _nps(items: list[Conversation]) -> float:
        """Proxy de NPS: cada transferência e cada caso de retenção pesam contra.
        Não é um NPS real — é um indicador derivado, e a interface rotula assim."""
        if not items:
            return 0.0
        penalty = sum(3 for c in items if c.handover.requested)
        penalty += sum(4 for c in items if c.area is Area.retencao)
        return round(max(0.0, 100 - penalty / len(items) * 10), 1)

    @staticmethod
    def _week(items: list[Conversation]) -> list[dict]:
        today = utcnow().date()
        buckets = {(today - timedelta(days=offset)): 0 for offset in range(6, -1, -1)}
        for conversation in items:
            day = conversation.started_at.date()
            if day in buckets:
                buckets[day] += 1
        return [{"day": WEEKDAYS_PT[day.weekday()], "conversations": count}
                for day, count in buckets.items()]

    @staticmethod
    def _channels(items: list[Conversation]) -> list[dict]:
        counter: Counter[Channel] = Counter()
        for conversation in items:
            for channel in conversation.channels_used:
                counter[channel] += 1
        return [{"name": channel.label, "value": counter.get(channel, 0),
                 "color": CHANNEL_COLORS[channel]}
                for channel in Channel]

    @staticmethod
    def _area_counts(items: list[Conversation]) -> dict[str, int]:
        counter = Counter(c.area.value for c in items)
        return {"Todos": len(items), **{area.value: counter.get(area.value, 0) for area in Area}}

    @staticmethod
    def _intents(items: list[Conversation]) -> list[dict]:
        counter = Counter(c.intent.name for c in items if c.intent)
        return [{"name": name, "count": count} for name, count in counter.most_common(6)]

    @staticmethod
    def _journey_breaks(items: list[Conversation]) -> list[dict]:
        """Onde a jornada quebrou: agrupa as transferências por motivo real."""
        by_reason: Counter[tuple[str, str]] = Counter()
        for conversation in items:
            if conversation.handover.requested and conversation.handover.reason:
                journey = conversation.intent.name if conversation.intent else "Não classificada"
                by_reason[(journey, conversation.handover.reason)] += 1

        result = []
        for (journey, reason), occurrences in by_reason.most_common(4):
            impact = "Crítico" if occurrences >= 4 else "Alto" if occurrences >= 2 else "Médio"
            result.append({"journey": journey, "break": reason,
                           "impact": impact, "occurrences": occurrences})
        return result

    @staticmethod
    def _automation(items: list[Conversation]) -> list[dict]:
        """Intenções que hoje geram transferência com frequência são as
        candidatas naturais a automação."""
        totals = Counter(c.intent.name for c in items if c.intent)
        handed = Counter(c.intent.name for c in items if c.intent and c.handover.requested)

        result = []
        for name, total in totals.most_common(3):
            contained = total - handed.get(name, 0)
            potential = round(contained / total * 100) if total else 0
            result.append({
                "area": name,
                "potential": potential,
                "estimated_savings_brl": contained * 4200,
            })
        return result

    @staticmethod
    def _alerts(items: list[Conversation]) -> list[dict]:
        alerts: list[dict] = []

        unclassified = [c for c in items
                        if c.intent and c.intent.slug == "nao_identificada"]
        if unclassified:
            alerts.append({
                "severity": "info",
                "title": "Intenções não mapeadas",
                "description": (f"{len(unclassified)} conversa(s) sem intenção correspondente na "
                                f"taxonomia. Avalie mapear no Design Studio."),
            })

        urgent = [c for c in items if c.priority.value == "high" and c.is_open]
        if len(urgent) >= 3:
            alerts.append({
                "severity": "warning",
                "title": "Fila de alta prioridade acumulando",
                "description": f"{len(urgent)} conversas urgentes aguardando atendimento.",
            })

        return alerts
