"""Ingestão de canais — RF001.

Único ponto de entrada de interações no hub. Qualquer canal, existente ou futuro,
chega por aqui e produz o mesmo evento conversacional interno.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from ....application.use_cases.ingest_message import IngestCommand
from ....container import Container, get_container
from ....domain.value_objects import Channel
from ..mappers import intent_to_dto
from ..schemas import ErrorResponse, HubReplyResponse, InboundMessageRequest

router = APIRouter(prefix="/api/v1/channels", tags=["Ingestão de Canais"])


@router.post(
    "/{channel}/messages",
    response_model=HubReplyResponse,
    status_code=status.HTTP_200_OK,
    summary="Entregar uma mensagem de cliente ao hub",
    responses={403: {"model": ErrorResponse, "description": "Consentimento ausente (LGPD)"}},
    description=(
        "Recebe uma mensagem vinda de um canal e devolve a resposta já pronta para "
        "ser entregue ao cliente.\n\n"
        "Uma única chamada percorre os seis requisitos funcionais: normaliza o evento "
        "(RF001), recupera o contexto do cliente (RF003), classifica a intenção (RF002), "
        "roteia para o fluxo e consulta os sistemas internos (RF004), aplica a persona "
        "da Claro (RF006) e avalia se o caso deve sair do bot (RF005).\n\n"
        "**Para integrar um canal novo, este é o único endpoint necessário.**\n\n"
        "Envie `external_id` com o identificador do cliente naquele canal. Quando o "
        "mesmo cliente aparecer em outro canal, `context_recovered` volta `true` e "
        "`context_note` descreve a migração — é a evidência observável da continuidade."
    ),
)
async def ingest(
    channel: Channel = Path(description="Canal de origem da mensagem."),
    payload: InboundMessageRequest = ...,
    container: Container = Depends(get_container),
) -> HubReplyResponse:
    try:
        result = await container.ingest_message.execute(IngestCommand(
            channel=channel, text=payload.text, customer_id=payload.customer_id,
            external_id=payload.external_id, consent=payload.consent,
        ))
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc

    return HubReplyResponse(
        conversation_id=result.conversation_id, session_id=result.session_id,
        customer_id=result.customer_id, channel=result.channel, reply=result.reply,
        intent=intent_to_dto(result.intent), flow=result.flow,
        persona_applied=result.persona_applied, context_recovered=result.context_recovered,
        context_note=result.context_note, handover_triggered=result.handover_triggered,
        handover_reason=result.handover_reason, services_consulted=result.services_consulted,
        turns=result.turns,
    )


@router.get(
    "",
    summary="Listar os canais integrados",
    description=("Canais que o hub aceita hoje e a configuração de tom de voz de cada um. "
                 "Acrescentar um canal aqui não exige alteração no núcleo (RNF004)."),
)
async def list_channels(container: Container = Depends(get_container)) -> list[dict]:
    config = await container.get_studio_config.execute()
    return [
        {
            "channel": channel.value,
            "label": channel.label,
            "studio_id": channel.studio_id,
            "endpoint": f"/api/v1/channels/{channel.value}/messages",
            "persona": (lambda c: {
                "formality": c.formality_label,
                "emoji": c.useEmoji,
                "max_length": c.maxLength,
            } if c else None)(config.channel(channel.studio_id)),
        }
        for channel in Channel
    ]
