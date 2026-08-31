"""Canal WhatsApp — WhatsApp Business Cloud API.

Diferente dos demais canais, o WhatsApp não lê a resposta na mesma requisição:
a Meta entrega a mensagem por webhook e a resposta tem de ser empurrada de volta
por outra chamada. Toda essa assimetria fica contida neste adaptador — o núcleo
processa a mensagem exatamente como processa qualquer outra.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse

from ....application.use_cases.ingest_message import IngestCommand
from ....container import Container, get_container
from ....domain.value_objects import Channel
from ..schemas.error_response import ErrorResponse
from ..schemas.whatsapp_send_request import WhatsAppSendRequest
from ..schemas.whatsapp_status_response import WhatsAppStatusResponse

log = logging.getLogger("hub.whatsapp.webhook")

router = APIRouter(prefix="/api/v1/channels/whatsapp", tags=["Ingestão de Canais"])


@router.get(
    "/webhook",
    response_class=PlainTextResponse,
    summary="Verificação do webhook (handshake da Meta)",
    description=("Chamado **uma vez pela Meta** ao cadastrar o webhook no painel do app. "
                 "O hub devolve o `hub.challenge` recebido se o `hub.verify_token` bater "
                 "com `WHATSAPP_VERIFY_TOKEN`.\n\n"
                 "Configure no painel da Meta:\n"
                 "- URL de callback: `<PUBLIC_URL>/api/v1/channels/whatsapp/webhook`\n"
                 "- Campo a assinar: `messages`"),
    responses={403: {"model": ErrorResponse, "description": "Token de verificação inválido"}},
)
async def verify_webhook(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    container: Container = Depends(get_container),
) -> str:
    try:
        return container.whatsapp.verify_subscription(mode, token, challenge)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Receber mensagens do WhatsApp",
    description=("Endpoint que a Meta chama a cada mensagem recebida no número do MVP.\n\n"
                 "O adaptador valida a assinatura `X-Hub-Signature-256`, extrai as "
                 "mensagens de texto e entrega cada uma ao mesmo caso de uso de ingestão "
                 "que atende os demais canais — o telefone do cliente entra como "
                 "`external_id` e o hub resolve o `customer_id`.\n\n"
                 "Responde 200 imediatamente e processa em segundo plano: a Meta reenvia "
                 "o evento se a resposta demorar, o que geraria mensagem duplicada."),
    responses={403: {"model": ErrorResponse, "description": "Assinatura inválida"}},
)
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
    signature: str | None = Header(None, alias="X-Hub-Signature-256"),
    container: Container = Depends(get_container),
) -> dict:
    raw = await request.body()

    try:
        container.whatsapp.verify_signature(raw, signature)
    except PermissionError as exc:
        log.warning("Webhook rejeitado: %s", exc)
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc

    payload = await request.json()
    messages = container.whatsapp.parse_webhook(payload)

    for message in messages:
        background.add_task(_process, container, message)

    return {"received": len(messages)}


async def _process(container: Container, message) -> None:
    """Processa a mensagem e devolve a resposta pelo WhatsApp."""
    try:
        result = await container.ingest_message.execute(IngestCommand(
            channel=Channel.whatsapp,
            text=message.text,
            external_id=message.wa_id,
        ))
        await container.whatsapp.send(message.wa_id, result.reply)
        log.info("WhatsApp %s → intenção %s (%.0f%%), handover=%s",
                 message.wa_id[-4:], result.intent.name,
                 result.intent.confidence * 100, result.handover_triggered)
    except Exception:  # noqa: BLE001
        # Uma mensagem que falha não pode derrubar o processamento das demais.
        log.exception("Falha ao processar mensagem do WhatsApp %s", message.wa_id[-4:])


@router.get(
    "/status",
    response_model=WhatsAppStatusResponse,
    summary="Status da integração com o WhatsApp",
    description=("Diz se o canal está habilitado, quais variáveis de ambiente faltam e "
                 "qual URL cadastrar como webhook no painel da Meta.\n\n"
                 "**Nunca devolve token nem segredo** — apenas se estão presentes."),
)
async def whatsapp_status(container: Container = Depends(get_container)) -> WhatsAppStatusResponse:
    return WhatsAppStatusResponse(
        **container.whatsapp.status(container.settings.public_url))


@router.post(
    "/send",
    summary="Enviar uma mensagem de teste pelo WhatsApp",
    description=("Envia texto direto pelo número do MVP, sem passar pelo núcleo "
                 "conversacional. Serve para validar credenciais e a lista de "
                 "destinatários de teste antes da demonstração.\n\n"
                 "Se `to` for omitido, usa `WHATSAPP_DEFAULT_RECIPIENT`."),
    responses={503: {"model": ErrorResponse, "description": "Canal não habilitado"}},
)
async def send_test(
    payload: WhatsAppSendRequest,
    container: Container = Depends(get_container),
) -> dict:
    recipient = payload.to or container.settings.whatsapp.default_recipient
    if not recipient:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Informe `to` ou configure WHATSAPP_DEFAULT_RECIPIENT no .env.")
    try:
        return await container.whatsapp.send(recipient, payload.text)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
