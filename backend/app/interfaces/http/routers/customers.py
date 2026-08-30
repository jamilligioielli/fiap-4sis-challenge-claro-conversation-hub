"""Console — clientes. Alimenta a tela de Contexto do Cliente."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from ....container import Container, get_container
from ..mappers import customer_to_dto
from ..schemas import CustomerContextResponse, ErrorResponse

router = APIRouter(prefix="/api/v1/customers", tags=["Console · Clientes"])


@router.get(
    "/{customer_id}/context",
    response_model=CustomerContextResponse,
    responses={404: {"model": ErrorResponse, "description": "Cliente não encontrado"}},
    summary="Visão 360° do cliente",
    description=("Perfil, plano contratado, produtos ativos, histórico consolidado entre "
                 "canais, elegibilidade para upgrade e risco de churn.\n\nÉ este contexto "
                 "que alimenta as sugestões de IA e o atendente humano — e é por existir "
                 "num só lugar que o cliente não precisa se reapresentar a cada canal.\n\n"
                 "Toda consulta é registrada na trilha de auditoria (LGPD)."),
)
async def get_context(
    customer_id: str = Path(description="Id do cliente no hub."),
    container: Container = Depends(get_container),
) -> CustomerContextResponse:
    context = await container.customer_context.execute(customer_id)
    if context is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return customer_to_dto(context.customer, context.conversations, context.upgrade_options)
