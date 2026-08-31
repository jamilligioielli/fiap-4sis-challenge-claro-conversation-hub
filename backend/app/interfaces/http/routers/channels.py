"""Ingestão de canais — ponto de entrada único das interações."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from ....application.dto.ingest_command import IngestCommand
from ....container import Container, get_container
from ....domain.value_objects.channel import Channel
from ....domain.value_objects.response_source import ResponseSource
from ....domain.value_objects.unidentified_intent import UNIDENTIFIED
from ..mappers import intent_to_dto
from ..schemas.error_response import ErrorResponse
from ..schemas.greeting_response import GreetingResponse
from ..schemas.hub_reply_response import HubReplyResponse
from ..schemas.inbound_message_request import InboundMessageRequest
from ..schemas.start_conversation_request import StartConversationRequest

router = APIRouter(prefix="/api/v1/channels", tags=["Ingestão de Canais"])


@router.post(
    "/{channel}/messages",
    response_model=HubReplyResponse,
    summary="Entregar uma mensagem de cliente ao hub",
    responses={403: {"model": ErrorResponse, "description": "Consentimento ausente"}},
    description=(
        "Recebe uma mensagem vinda de um canal e devolve a resposta pronta para ser "
        "entregue ao cliente.\n\n"
        "Uma única chamada normaliza o evento, recupera o contexto do cliente, "
        "classifica a intenção, roteia para o fluxo de negócio, consulta os sistemas "
        "internos, redige a resposta na voz da marca e avalia se o caso deve sair do "
        "atendimento automatizado.\n\n"
        "**Para integrar um canal novo, este é o único endpoint necessário.**\n\n"
        "Envie `external_id` com o identificador do cliente naquele canal. Quando o "
        "mesmo cliente aparecer em outro canal, `context_recovered` volta `true` — e, "
        "havendo assunto em aberto, o hub devolve `awaiting_context_confirmation` e "
        "pergunta antes de prosseguir, em vez de presumir o que o cliente quer."
    ),
)
async def ingest(
    channel: Channel = Path(description="Canal de origem da mensagem."),
    payload: InboundMessageRequest = ...,
    container: Container = Depends(get_container),
) -> HubReplyResponse:
    # Espera o cliente terminar de escrever. A chamada fica aberta durante a
    # janela de silêncio; se outra mensagem do mesmo cliente chegar antes, ela
    # assume o lote e esta retorna sem resposta — quem responde é a última.
    chave = payload.customer_id or payload.external_id or "anonimo"
    texto = await container.debouncer.submit(chave, payload.text)
    if texto is None:
        return _superseded(channel)

    try:
        result = await container.ingest_message.execute(IngestCommand(
            channel=channel, text=texto, customer_id=payload.customer_id,
            external_id=payload.external_id, consent=payload.consent,
        ))
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc

    return HubReplyResponse(
        conversation_id=result.conversation_id, session_id=result.session_id,
        customer_id=result.customer_id, channel=result.channel, reply=result.reply,
        intent=intent_to_dto(result.intent), flow=result.flow,
        persona_applied=result.persona_applied, persona_version=result.persona_version,
        response_source=result.response_source.value, response_model=result.response_model,
        context_recovered=result.context_recovered, context_note=result.context_note,
        awaiting_context_confirmation=result.awaiting_context_confirmation,
        handover_triggered=result.handover_triggered,
        handover_reason=result.handover_reason,
        services_consulted=result.services_consulted, turns=result.turns,
        awaiting_nps=result.awaiting_nps,
        conversation_closed=result.conversation_closed,
        nps_score=result.nps_score,
    )


def _superseded(channel: Channel) -> HubReplyResponse:
    """Resposta de uma mensagem que foi absorvida por outra mais recente.

    Não é erro: é o desenho funcionando. O cliente mandou "oi" e, antes de a
    janela fechar, mandou o pedido de verdade — as duas viram uma rodada só, e
    a resposta sai na chamada que fechou o lote."""
    return HubReplyResponse(
        conversation_id="", session_id="", customer_id="", channel=channel,
        reply="", intent=intent_to_dto(UNIDENTIFIED), flow="agrupada",
        persona_applied="", persona_version=0,
        response_source=ResponseSource.template.value, response_model=None,
        context_recovered=False, context_note=None,
        awaiting_context_confirmation=False, handover_triggered=False,
        handover_reason=None, services_consulted=[], turns=0,
        superseded=True,
    )


@router.post(
    "/conversations",
    response_model=GreetingResponse,
    responses={404: {"model": ErrorResponse, "description": "Cliente não encontrado"}},
    summary="Abrir uma conversa e receber a saudação do assistente",
    description=(
        "Abre a conversa antes da primeira mensagem do cliente, para que o assistente "
        "cumprimente por iniciativa própria em vez de deixá-lo diante de uma tela vazia.\n\n"
        "Se já houver conversa em andamento para este cliente, ela é retomada e "
        "`resumed` volta `true` — nenhuma saudação nova é gerada."
    ),
)
async def start_conversation(
    payload: StartConversationRequest,
    container: Container = Depends(get_container),
) -> GreetingResponse:
    started = await container.start_conversation.execute(payload.customer_id, payload.channel)
    if started is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

    return GreetingResponse(
        conversation_id=started.conversation_id, session_id=started.session_id,
        customer_id=started.customer_id, greeting=started.greeting,
        persona_applied=started.persona_applied, persona_version=started.persona_version,
        response_source=started.response_source.value, response_model=started.response_model,
        resumed=started.resumed,
    )


@router.get(
    "",
    summary="Listar os canais integrados",
    description=("Canais que o hub aceita e a configuração de tom de voz de cada um. "
                 "O campo `simulatable` indica quais podem ser exercitados por texto: "
                 "a URA é um canal de voz por ligação, e simulá-la por escrito daria "
                 "uma impressão falsa do que ela é."),
)
async def list_channels(container: Container = Depends(get_container)) -> list[dict]:
    config = await container.get_studio_config.execute()
    result = []
    for channel in Channel:
        channel_config = config.channel(channel.studio_id)
        result.append({
            "channel": channel.value,
            "label": channel.label,
            "studio_id": channel.studio_id,
            "simulatable": channel.simulatable,
            "endpoint": f"/api/v1/channels/{channel.value}/messages",
            "persona": {
                "formality": channel_config.formality_label,
                "emoji": channel_config.useEmoji,
                "max_length": channel_config.maxLength,
            } if channel_config else None,
        })
    return result
