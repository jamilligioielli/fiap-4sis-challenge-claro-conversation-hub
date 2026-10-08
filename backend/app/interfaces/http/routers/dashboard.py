"""Console — dashboard. Métricas derivadas das conversas reais."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from ....container import Container, get_container
from ....domain.services.nps_analytics_service import NpsGroupStats
from ..schemas.dashboard_response import DashboardResponse
from ..schemas.nps_comparison_response import (NpsComparisonDelta, NpsComparisonResponse,
                                               NpsGroupResponse, NpsPercentages)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Console · Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Métricas operacionais",
    description=("Volume por canal, taxa de resolução digital, transferências para humano, "
                 "distribuição de intenções, jornadas com ruptura e oportunidades de "
                 "automação.\n\nOs números são **calculados a partir das conversas que o hub "
                 "processou**, não constantes: mandar uma mensagem por qualquer canal move "
                 "o indicador na tela.\n\nA API devolve números crus; a formatação de "
                 "exibição é responsabilidade da interface."),
)
async def metrics(
    area: str | None = Query(None, description="Filtra por área. Omitido = todas."),
    container: Container = Depends(get_container),
) -> DashboardResponse:
    result = await container.dashboard_metrics.execute(area)
    return DashboardResponse(**asdict(result))


def _group(stats: NpsGroupStats) -> NpsGroupResponse:
    return NpsGroupResponse(
        total=stats.total, average_score=stats.average_score, nps=stats.nps,
        promoters=stats.promoters, passives=stats.passives, detractors=stats.detractors,
        percentages=NpsPercentages(**stats.percentages),
        surveys_sent=stats.surveys_sent, unanswered=stats.unanswered,
    )


@router.get(
    "/nps-comparison",
    response_model=NpsComparisonResponse,
    summary="NPS do atendimento automatizado versus o humano",
    description=("Separa as notas de satisfação entre os atendimentos que o assistente "
                 "conduziu sozinho e os que passaram por um atendente humano — por "
                 "transferência, resposta do atendente ou encerramento pelo console.\n\n"
                 "Só notas respondidas entram na média; pesquisas sem resposta aparecem "
                 "em `unanswered`. Respeita o mesmo filtro de área do painel."),
)
async def nps_comparison(
    area: str | None = Query(None, description="Filtra por área. Omitido = todas."),
    container: Container = Depends(get_container),
) -> NpsComparisonResponse:
    result = await container.nps_comparison.execute(area)
    return NpsComparisonResponse(
        area=area or "Todos",
        bot=_group(result.bot), agent=_group(result.agent), overall=_group(result.overall),
        comparison=NpsComparisonDelta(
            score_difference=result.score_difference,
            nps_difference=result.nps_difference,
            agent_better=result.agent_better,
        ),
    )
