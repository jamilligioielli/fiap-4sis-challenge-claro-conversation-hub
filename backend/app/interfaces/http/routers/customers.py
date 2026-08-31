"""Clientes — lista para simulação e visão consolidada para o console."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from ....container import Container, get_container
from ..mappers import conversation_to_list_item, customer_to_context, customer_to_summary
from ..schemas.conversation_list_item import ConversationListItem
from ..schemas.customer_context_response import CustomerContextResponse
from ..schemas.customer_summary_response import CustomerSummaryResponse
from ..schemas.error_response import ErrorResponse

router = APIRouter(prefix="/api/v1/customers", tags=["Clientes"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Cliente não encontrado"}}


@router.get(
    "",
    response_model=list[CustomerSummaryResponse],
    summary="Listar clientes disponíveis",
    description=("Alimenta a escolha de persona no simulador: quem existe, como cada um "
                 "costuma se comportar e se já há conversa em andamento.\n\n"
                 "O campo `persona_summary` entra no contexto do assistente, de modo que "
                 "a resposta considere quem está do outro lado."),
)
async def list_customers(
    container: Container = Depends(get_container),
) -> list[CustomerSummaryResponse]:
    entries = await container.list_customers.execute()
    return [customer_to_summary(c, count, current) for c, count, current in entries]


@router.get(
    "/{customer_id}/context",
    response_model=CustomerContextResponse,
    responses=NOT_FOUND,
    summary="Visão consolidada do cliente",
    description=("Perfil, plano contratado, produtos ativos, histórico entre canais, "
                 "elegibilidade para upgrade e risco de saída.\n\n"
                 "É este contexto que alimenta as sugestões do assistente e o atendente "
                 "humano — e é por existir num só lugar que o cliente não precisa se "
                 "reapresentar a cada canal.\n\n"
                 "Toda consulta é registrada na trilha de auditoria."),
)
async def get_context(
    customer_id: str = Path(description="Identificador do cliente."),
    container: Container = Depends(get_container),
) -> CustomerContextResponse:
    context = await container.customer_context.execute(customer_id)
    if context is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
    return customer_to_context(context.customer, context.conversations,
                               context.upgrade_options)


@router.get(
    "/{customer_id}/conversations",
    response_model=list[ConversationListItem],
    summary="Conversas de um cliente",
    description=("Histórico de conversas daquele cliente, da mais recente para a mais "
                 "antiga. É o que permite, no simulador, voltar a uma conversa anterior "
                 "em vez de recomeçar do zero a cada vez."),
)
async def list_customer_conversations(
    customer_id: str,
    container: Container = Depends(get_container),
) -> list[ConversationListItem]:
    conversations = await container.list_conversations_for_customer(customer_id)
    result = []
    for conversation in conversations:
        transcript = await container.conversations.transcript(conversation.id)
        result.append(conversation_to_list_item(conversation, len(transcript)))
    return result
