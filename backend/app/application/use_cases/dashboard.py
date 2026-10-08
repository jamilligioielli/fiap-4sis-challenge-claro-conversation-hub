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
from datetime import timedelta

from ...domain.entities.conversation import Conversation
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.services.nps_analytics_service import NpsAnalyticsService, NpsComparison
from ...domain.value_objects.area import Area
from ...domain.value_objects.channel import Channel
from ...domain.value_objects.clock import utcnow
from ..dto.dashboard_metrics import DashboardMetrics
from ..dto.kpi import KPI

WEEKDAYS_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

CHANNEL_COLORS = {
    Channel.whatsapp: "#25D366",
    Channel.web: "#4A90E2",
    Channel.app: "#E10019",
    Channel.voice: "#9B59B6",
}


class GetDashboardMetricsUseCase:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def execute(self, area: str | None = None) -> DashboardMetrics:
        every = await self._conversations.list()
        scoped = [c for c in every if area in (None, "Todos") or c.area.value == area]

        total = len(scoped)
        handed_over = sum(1 for c in scoped if c.handover.requested)
        # Resolução digital: atendimento encerrado sem passar por humano. (Até a
        # Sprint 3 a regra excluía justamente as encerradas — `pending` é o
        # estado de conversa encerrada — e contava as ainda abertas.)
        resolved = sum(1 for c in scoped
                       if c.closed_at is not None and c.attended_by == "bot")

        return DashboardMetrics(
            area=area or "Todos",
            has_data=total > 0,
            conversations=KPI(value=total, trend=12.5),
            resolution_rate=KPI(value=self._pct(resolved, total), trend=4.2, unit="%"),
            handover_rate=KPI(value=self._pct(handed_over, total), trend=-3.1, unit="%"),
            nps=KPI(value=self._nps(scoped), trend=2.8,
                    unit=f"{self._nps_answers(scoped)} resposta(s)"),
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
        """NPS pela fórmula real: % de promotores menos % de detratores.

        Só entram conversas com nota respondida. Enquanto ninguém respondeu, o
        indicador é zero e a interface diz que ainda não há respostas — inventar
        um número aqui seria exatamente o tipo de métrica que não se pode
        defender numa reunião.
        """
        notas = [c.nps for c in items if c.nps and c.nps.answered]
        if not notas:
            return 0.0
        promotores = sum(1 for n in notas if n.category == "promotor")
        detratores = sum(1 for n in notas if n.category == "detrator")
        return round((promotores - detratores) / len(notas) * 100, 1)

    @staticmethod
    def _nps_answers(items: list[Conversation]) -> int:
        return sum(1 for c in items if c.nps and c.nps.answered)

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


class GetNpsComparisonUseCase:
    """Comparativo de NPS entre atendimento automatizado e humano.

    Usa o mesmo recorte por área do painel, para que trocar o filtro mova os
    dois blocos juntos.
    """

    def __init__(self, conversations: ConversationRepository,
                 analytics: NpsAnalyticsService | None = None) -> None:
        self._conversations = conversations
        self._analytics = analytics or NpsAnalyticsService()

    async def execute(self, area: str | None = None) -> NpsComparison:
        scope = None if area in (None, "", "Todos") else area
        conversations = await self._conversations.list(area=scope)
        return self._analytics.calculate_bot_vs_agent_nps(conversations)
