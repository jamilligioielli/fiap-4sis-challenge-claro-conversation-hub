"""Console — conversas. Alimenta o Inbox e a tela de Conversa Ativa."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from ....application.dto.list_conversations_query import ListConversationsQuery
from ....container import Container, get_container
from ..mappers import conversation_to_list_item, intent_to_dto, message_to_dto
from ..schemas.agent_message_request import AgentMessageRequest
from ..schemas.ai_panel_response import AIPanelResponse
from ..schemas.close_conversation_request import CloseConversationRequest
from ..schemas.close_conversation_response import CloseConversationResponse
from ..schemas.conversation_detail_response import ConversationDetailResponse
from ..schemas.conversation_list_item import ConversationListItem
from ..schemas.error_response import ErrorResponse
from ..schemas.handover_request import HandoverRequest
from ..schemas.message_response import MessageResponse

router = APIRouter(prefix="/api/v1/conversations", tags=["Console · Conversas"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Conversa não encontrada"}}


@router.get(
    "",
    response_model=list[ConversationListItem],
    summary="Listar a fila de conversas (Inbox)",
    description=("Fila única com as conversas de **todos os canais**. Os filtros são "
                 "combináveis e correspondem aos controles da tela de Inbox.\n\n"
                 "O campo `timestamp` já vem como rótulo relativo pronto para exibição."),
)
async def list_conversations(
    area: str | None = Query(None, description="Suporte, Vendas, Financeiro, Marketing, Retenção, Técnico."),
    channel: str | None = Query(None, description="whatsapp, web, app ou voice."),
    status_filter: str | None = Query(None, alias="status",
                                      description="active, waiting, transferred ou pending."),
    search: str | None = Query(None, description="Busca em nome do cliente e última mensagem."),
    container: Container = Depends(get_container),
) -> list[ConversationListItem]:
    items = await container.list_conversations.execute(ListConversationsQuery(
        area=area, channel=channel, status=status_filter, search=search))
    return [conversation_to_list_item(c) for c in items]


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    responses=NOT_FOUND,
    summary="Abrir uma conversa com transcrição e painel de IA",
    description=("Transcrição completa mais o painel lateral do atendente: intenção "
                 "detectada, resumo automático, próximas melhores ações e insights do "
                 "cliente.\n\nÉ o que permite ao atendente assumir a conversa sem pedir "
                 "que o cliente repita qualquer informação."),
)
async def get_conversation(
    conversation_id: str = Path(description="Id da conversa."),
    container: Container = Depends(get_container),
) -> ConversationDetailResponse:
    detail = await container.get_conversation.execute(conversation_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")

    conversation = detail.conversation
    return ConversationDetailResponse(
        id=conversation.id, customer_id=conversation.customer_id,
        customer_name=conversation.customer_name or "Cliente não identificado",
        status=conversation.status, area=conversation.area, priority=conversation.priority,
        channels_used=conversation.channels_used, started_at=conversation.started_at,
        initiated_by_company=conversation.initiated_by_company,
        messages=[message_to_dto(m) for m in detail.messages],
        ai=AIPanelResponse(
            intent=intent_to_dto(conversation.intent),
            summary=detail.summary, suggestions=detail.suggestions,
            insights=detail.insights, handover=conversation.handover.model_dump(mode="json"),
        ),
    )


@router.post(
    "/{conversation_id}/handover",
    response_model=ConversationListItem,
    responses=NOT_FOUND,
    summary="Transferir a conversa para um atendente humano",
    description=("Empacota a sessão — transcrição, intenções e sistemas já consultados — e "
                 "move a conversa para a fila de atendimento humano.\n\nA transferência é "
                 "registrada na trilha de auditoria. Uma conversa transferida não volta "
                 "sozinha ao bot: quem devolve é o atendente, explicitamente."),
)
async def request_handover(
    conversation_id: str,
    payload: HandoverRequest,
    container: Container = Depends(get_container),
) -> ConversationListItem:
    conversation = await container.request_handover.execute(
        conversation_id, payload.reason, payload.agent)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")
    return conversation_to_list_item(conversation)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND,
    summary="Responder como atendente humano",
    description=("Mensagem enviada pelo atendente a partir do console. Se o canal não for "
                 "informado, a resposta sai pelo último canal usado pelo cliente — quem "
                 "escolhe o canal é o cliente, não o console."),
)
async def reply_as_agent(
    conversation_id: str,
    payload: AgentMessageRequest,
    container: Container = Depends(get_container),
) -> MessageResponse:
    message = await container.reply_as_agent.execute(
        conversation_id, payload.text, payload.channel)
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")
    return message_to_dto(message)


@router.post(
    "/{conversation_id}/close",
    response_model=CloseConversationResponse,
    responses=NOT_FOUND,
    summary="Encerrar o atendimento e disparar a pesquisa de satisfação",
    description=(
        "Encerra o atendimento e envia a pesquisa de NPS ao cliente pelo último canal "
        "que ele usou, na mesma mensagem da despedida.\n\n"
        "A pesquisa sai igual quando quem encerra é o assistente — ao reconhecer uma "
        "despedida do cliente — e quando é o atendente humano, por este endpoint. Medir "
        "só o atendimento automatizado deixaria cego justamente o canal mais caro.\n\n"
        "A conversa fica em espera até a nota chegar: a próxima mensagem do cliente é "
        "lida como resposta à pesquisa. Quem não quiser responder é encerrado do mesmo "
        "jeito — o hub insiste no máximo uma vez."
    ),
)
async def close_conversation(
    conversation_id: str,
    payload: CloseConversationRequest,
    container: Container = Depends(get_container),
) -> CloseConversationResponse:
    # Um lote de mensagens em espera não faz mais sentido depois do
    # encerramento: seria responder a um atendimento que já acabou.
    resultado = await container.close_conversation.execute(
        conversation_id, closed_by=payload.agent, with_survey=payload.survey)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversa não encontrada")

    await container.debouncer.flush(resultado.conversation.customer_id)
    return CloseConversationResponse(
        conversation=conversation_to_list_item(resultado.conversation),
        survey_sent=resultado.survey_sent,
        survey_message=resultado.survey_message,
    )
