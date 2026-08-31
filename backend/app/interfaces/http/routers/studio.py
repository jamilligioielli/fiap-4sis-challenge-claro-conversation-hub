"""Console — Design Studio.

A persona é um parâmetro do sistema, não código espalhado pelas integrações.
O que se salva aqui vale para todos os canais na próxima mensagem, sem deploy.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from ....container import Container, get_container
from ....domain.studio.studio_config import StudioConfig
from ..schemas.error_response import ErrorResponse
from ..schemas.persona_preview_request import PersonaPreviewRequest
from ..schemas.persona_preview_response import (ChannelPreview,
                                                PersonaPreviewResponse)

router = APIRouter(prefix="/api/v1/studio", tags=["Console · Design Studio"])


@router.get(
    "/config",
    response_model=StudioConfig,
    summary="Ler a configuração de persona",
    description=("Persona da marca, intenções mapeadas, guardrails e a configuração de tom "
                 "de voz de cada canal.\n\nO canal `voice` traz um bloco `voiceConfig` "
                 "adicional (TTS, script da URA, menus, transbordo e glossário de "
                 "pronúncia). Nenhum outro canal tem esse bloco — e nada no núcleo precisou "
                 "mudar para que ele existisse."),
)
async def get_config(container: Container = Depends(get_container)) -> StudioConfig:
    return await container.get_studio_config.execute()


@router.put(
    "/config",
    response_model=StudioConfig,
    summary="Salvar a configuração completa",
    description=("Substitui a configuração inteira. A alteração passa a valer na próxima "
                 "mensagem processada, em todos os canais, sem reinício do serviço."),
)
async def update_config(
    config: StudioConfig,
    container: Container = Depends(get_container),
) -> StudioConfig:
    return await container.update_studio_config.execute(config)


@router.patch(
    "/channels/{channel_id}",
    response_model=StudioConfig,
    responses={404: {"model": ErrorResponse, "description": "Canal não configurado"}},
    summary="Atualizar o tom de voz de um canal",
    description=("Atualização parcial de um canal, preservando os demais. É o que a tela "
                 "de editor de canal usa ao salvar.\n\nExemplo de corpo: "
                 "`{\"formalityLevel\": 20, \"useEmoji\": true}`"),
)
async def update_channel(
    channel_id: str = Path(description="whatsapp, webchat, app ou voice."),
    patch: dict = Body(examples=[{"formalityLevel": 20, "useEmoji": True, "maxLength": 160}]),
    container: Container = Depends(get_container),
) -> StudioConfig:
    config = await container.update_channel_config.execute(channel_id, patch)
    if config is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Canal '{channel_id}' não configurado")
    return config


@router.post(
    "/preview",
    response_model=PersonaPreviewResponse,
    summary="Pré-visualizar o efeito da persona em cada canal",
    description=(
        "Aplica a configuração vigente sobre uma mensagem de exemplo e devolve como ela "
        "sai em cada canal.\n\n"
        "Existe para tornar visível o que normalmente só se percebe conversando: mudar a "
        "formalidade ou desligar os emojis muda a fala em todos os canais ao mesmo tempo. "
        "O campo `persona_version` sobe a cada gravação, o que permite conferir na "
        "conversa que o ajuste realmente chegou até o cliente."
    ),
)
async def preview(
    payload: PersonaPreviewRequest,
    container: Container = Depends(get_container),
) -> PersonaPreviewResponse:
    result = await container.preview_persona.execute(
        payload.message, payload.channels, payload.customer_id)
    return PersonaPreviewResponse(
        persona_name=result.persona_name,
        persona_version=result.persona_version,
        original=result.original,
        previews=[ChannelPreview(**preview.__dict__) for preview in result.previews],
    )
