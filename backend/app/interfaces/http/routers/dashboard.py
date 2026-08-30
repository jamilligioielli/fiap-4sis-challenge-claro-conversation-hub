"""Console — dashboard. Métricas derivadas das conversas reais."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query

from ....container import Container, get_container
from ..schemas import DashboardResponse

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
