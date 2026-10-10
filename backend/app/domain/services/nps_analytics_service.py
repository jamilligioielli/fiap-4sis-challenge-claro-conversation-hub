"""Comparativo de NPS entre o atendimento automatizado e o humano.

O NPS do painel é um número só, e um número só esconde a pergunta que a
operação precisa responder: o cliente sai mais satisfeito quando o assistente
resolve sozinho ou quando um atendente assume? A resposta orienta onde investir
— automatizar mais uma jornada ou reforçar a equipe que atende os casos que
chegam a ela.

Regra pura, sem I/O: recebe as conversas e devolve os números. A faixa de cada
categoria vem de `NpsSurvey.category`, a mesma que alimenta o KPI de NPS do
painel — dois cálculos com fronteiras diferentes produziriam números que não
batem entre si.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..entities.conversation import Conversation


@dataclass(frozen=True)
class NpsGroupStats:
    """Números de um grupo de atendimentos (bot, humano ou todos)."""

    total: int = 0
    average_score: float | None = None
    nps: float | None = None
    promoters: int = 0
    passives: int = 0
    detractors: int = 0
    surveys_sent: int = 0
    unanswered: int = 0

    @property
    def percentages(self) -> dict[str, float]:
        if not self.total:
            return {"promoters": 0.0, "passives": 0.0, "detractors": 0.0}
        return {
            "promoters": round(self.promoters / self.total * 100, 1),
            "passives": round(self.passives / self.total * 100, 1),
            "detractors": round(self.detractors / self.total * 100, 1),
        }


@dataclass(frozen=True)
class NpsComparison:
    bot: NpsGroupStats = field(default_factory=NpsGroupStats)
    agent: NpsGroupStats = field(default_factory=NpsGroupStats)
    overall: NpsGroupStats = field(default_factory=NpsGroupStats)

    @property
    def score_difference(self) -> float | None:
        """Nota média do humano menos a do bot. `None` sem os dois lados."""
        if self.bot.average_score is None or self.agent.average_score is None:
            return None
        return round(self.agent.average_score - self.bot.average_score, 1)

    @property
    def nps_difference(self) -> float | None:
        if self.bot.nps is None or self.agent.nps is None:
            return None
        return round(self.agent.nps - self.bot.nps, 1)

    @property
    def agent_better(self) -> bool | None:
        diff = self.score_difference
        return None if diff is None else diff > 0


class NpsAnalyticsService:
    def calculate_bot_vs_agent_nps(self, conversations: list[Conversation]) -> NpsComparison:
        surveyed = [c for c in conversations if c.nps is not None]
        bot = [c for c in surveyed if c.attended_by == "bot"]
        agent = [c for c in surveyed if c.attended_by == "agent"]
        return NpsComparison(
            bot=self._stats(bot), agent=self._stats(agent), overall=self._stats(surveyed))

    @staticmethod
    def _stats(conversations: list[Conversation]) -> NpsGroupStats:
        """Só nota respondida entra na média.

        Pesquisa recusada ou ignorada fica de fora do cálculo, mas é contada à
        parte: um grupo com nota alta e 90% de silêncio não é o mesmo que um
        grupo com nota alta e todo mundo respondendo.
        """
        answered = [c.nps for c in conversations if c.nps is not None and c.nps.answered]
        scores = [n.score for n in answered if n.score is not None]
        promoters = sum(1 for n in answered if n.category == "promotor")
        passives = sum(1 for n in answered if n.category == "neutro")
        detractors = sum(1 for n in answered if n.category == "detrator")
        total = len(scores)

        return NpsGroupStats(
            total=total,
            average_score=round(sum(scores) / total, 1) if total else None,
            nps=round((promoters - detractors) / total * 100, 1) if total else None,
            promoters=promoters,
            passives=passives,
            detractors=detractors,
            surveys_sent=len(conversations),
            unanswered=len(conversations) - total,
        )
