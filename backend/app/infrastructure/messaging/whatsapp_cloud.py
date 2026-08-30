"""Adaptador da WhatsApp Business Cloud API (Meta Graph API).

É o primeiro canal *real* do hub, e serve como referência para os próximos: o
adaptador traduz o formato do canal para o comando de ingestão do hub na
entrada, e traduz a resposta do hub para o formato do canal na saída. Nada
disso encosta no núcleo — que continua sem saber que WhatsApp existe.

Entrada  (Meta → hub):  webhook  POST /api/v1/channels/whatsapp/webhook
Saída    (hub → Meta):  POST https://graph.facebook.com/{versão}/{phone_id}/messages
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

from ...domain.ports import OutboundGateway
from ...domain.value_objects import Channel
from ...settings import WhatsAppSettings

log = logging.getLogger("hub.whatsapp")


@dataclass(frozen=True)
class InboundWhatsAppMessage:
    """Uma mensagem extraída do payload do webhook."""
    wa_id: str            # telefone do cliente — o `external_id` deste canal
    text: str
    message_id: str
    profile_name: str | None = None
    timestamp: str | None = None


class WhatsAppSignatureError(PermissionError):
    """Assinatura do webhook inválida — o payload não veio da Meta."""


class WhatsAppCloudGateway(OutboundGateway):
    """Envio de mensagens para o cliente pelo WhatsApp."""

    channel = Channel.whatsapp

    def __init__(self, settings: WhatsAppSettings) -> None:
        self._s = settings

    @property
    def enabled(self) -> bool:
        return self._s.can_send

    async def send(self, to: str, text: str) -> dict:
        """`to` é o telefone em formato internacional, apenas dígitos."""
        if not self._s.can_send:
            raise RuntimeError(
                "WhatsApp não está habilitado. Defina WHATSAPP_ENABLED=true e as "
                "credenciais em .env — veja .env.example."
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        async with httpx.AsyncClient(timeout=self._s.timeout) as client:
            response = await client.post(
                self._s.graph_url,
                headers={"Authorization": f"Bearer {self._s.access_token}"},
                json=payload,
            )

        if response.status_code >= 400:
            # O erro da Meta é informativo; propagá-lo poupa muito tempo de
            # depuração (token expirado, número fora da lista de teste, etc.).
            detail = response.json().get("error", {}) if response.content else {}
            raise RuntimeError(
                f"WhatsApp recusou o envio ({response.status_code}): "
                f"{detail.get('message', response.text[:200])}"
            )

        return response.json()

    # ------------------------------------------------------------- webhook
    def verify_subscription(self, mode: str | None, token: str | None,
                            challenge: str | None) -> str:
        """Handshake de verificação do webhook (GET), feito uma vez pela Meta."""
        if mode == "subscribe" and token and token == self._s.verify_token:
            log.info("Webhook do WhatsApp verificado com sucesso")
            return challenge or ""
        raise PermissionError("Token de verificação do webhook não confere.")

    def verify_signature(self, raw_body: bytes, signature_header: str | None) -> None:
        """Confere o `X-Hub-Signature-256`.

        Sem o app secret configurado a checagem é pulada — e isso é registrado,
        porque significa que qualquer um pode postar mensagens forjadas no
        endpoint. Em produção o secret é obrigatório.
        """
        if not self._s.verifies_signature:
            log.warning("WHATSAPP_APP_SECRET ausente — webhook aceito sem validação "
                        "de assinatura. Não faça isso em produção.")
            return

        if not signature_header or not signature_header.startswith("sha256="):
            raise WhatsAppSignatureError("Cabeçalho X-Hub-Signature-256 ausente ou malformado.")

        expected = hmac.new(
            self._s.app_secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature_header.removeprefix("sha256=")):
            raise WhatsAppSignatureError("Assinatura do webhook não confere.")

    @staticmethod
    def parse_webhook(payload: dict) -> list[InboundWhatsAppMessage]:
        """Extrai as mensagens de texto do payload da Meta.

        O formato é aninhado e vem com muita coisa que não interessa aqui:
        confirmações de entrega, atualizações de status, mensagens de mídia.
        Só mensagens de texto viram interação no hub — mídia fica para a Fase 2.
        """
        messages: list[InboundWhatsAppMessage] = []

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # nomes de perfil vêm num array separado, indexado por wa_id
                profiles = {
                    contact.get("wa_id"): contact.get("profile", {}).get("name")
                    for contact in value.get("contacts", [])
                }

                for message in value.get("messages", []):
                    if message.get("type") != "text":
                        log.info("Mensagem do tipo '%s' ignorada (fora do escopo do MVP)",
                                 message.get("type"))
                        continue

                    wa_id = message.get("from", "")
                    body = (message.get("text") or {}).get("body", "").strip()
                    if not wa_id or not body:
                        continue

                    messages.append(InboundWhatsAppMessage(
                        wa_id=wa_id,
                        text=body,
                        message_id=message.get("id", ""),
                        profile_name=profiles.get(wa_id),
                        timestamp=message.get("timestamp"),
                    ))

        return messages

    # -------------------------------------------------------------- status
    def status(self, public_url: str) -> dict:
        """Diagnóstico para o console — nunca expõe token nem segredo."""
        return {
            "enabled": self._s.enabled,
            "configured": self._s.configured,
            "can_send": self._s.can_send,
            "api_version": self._s.api_version,
            "phone_number_id": self._mask(self._s.phone_number_id),
            "business_account_id": self._mask(self._s.business_account_id),
            "access_token": "configurado" if self._s.access_token else "ausente",
            "verify_token": "configurado" if self._s.verify_token else "ausente",
            "signature_validation": self._s.verifies_signature,
            "default_recipient": self._mask_phone(self._s.default_recipient),
            "webhook_url": f"{public_url.rstrip('/')}/api/v1/channels/whatsapp/webhook",
            "missing": self._s.missing(),
        }

    @staticmethod
    def _mask(value: str) -> str:
        if not value:
            return ""
        return value if len(value) <= 6 else f"{value[:4]}…{value[-4:]}"

    @staticmethod
    def _mask_phone(value: str) -> str:
        return f"…{value[-4:]}" if len(value) > 4 else value


class NullGateway(OutboundGateway):
    """Nenhum canal externo configurado.

    Usado quando o hub roda apenas com o simulador — a resposta volta pelo HTTP
    da própria chamada, e não há para onde empurrar mensagem.
    """

    channel = Channel.whatsapp
    enabled = False

    async def send(self, to: str, text: str) -> dict:
        raise RuntimeError(
            "Nenhum gateway de saída configurado. Habilite o WhatsApp em .env "
            "ou use o Simulador de Canais do console."
        )
