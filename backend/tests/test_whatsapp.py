"""Testes do adaptador da WhatsApp Business Cloud API.

O canal real é o que separa "protótipo de tela" de "integração". Estes testes
cobrem as três coisas que dão errado numa integração de webhook — assinatura,
formato do payload e credencial faltando — sem depender da Meta.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest

from app.infrastructure.messaging.whatsapp_cloud import (InboundWhatsAppMessage,
                                                         WhatsAppCloudGateway,
                                                         WhatsAppSignatureError)
from app.settings import WhatsAppSettings

SECRET = "segredo-do-app"


def gateway(**overrides) -> WhatsAppCloudGateway:
    base = dict(enabled=True, phone_number_id="123456", access_token="EAAtoken",
                verify_token="token-verificacao", app_secret=SECRET,
                business_account_id="789")
    return WhatsAppCloudGateway(WhatsAppSettings(**{**base, **overrides}))


def webhook_payload(text: str = "oi", wa_id: str = "5511999990001",
                    kind: str = "text") -> dict:
    message: dict = {"from": wa_id, "id": "wamid.ABC", "timestamp": "1756500000",
                     "type": kind}
    if kind == "text":
        message["text"] = {"body": text}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "789", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "contacts": [{"wa_id": wa_id, "profile": {"name": "Maria"}}],
            "messages": [message],
        }}]}],
    }


# ================================================================ handshake
class TestVerificacaoDoWebhook:
    def test_devolve_o_desafio_quando_o_token_confere(self):
        assert gateway().verify_subscription(
            "subscribe", "token-verificacao", "desafio-123") == "desafio-123"

    def test_recusa_token_diferente(self):
        with pytest.raises(PermissionError):
            gateway().verify_subscription("subscribe", "outro", "desafio")

    def test_recusa_modo_diferente_de_subscribe(self):
        with pytest.raises(PermissionError):
            gateway().verify_subscription("unsubscribe", "token-verificacao", "d")


# ================================================================ assinatura
class TestAssinatura:
    def test_aceita_assinatura_valida(self):
        corpo = json.dumps(webhook_payload()).encode()
        assinatura = "sha256=" + hmac.new(SECRET.encode(), corpo, hashlib.sha256).hexdigest()

        gateway().verify_signature(corpo, assinatura)  # não levanta

    def test_recusa_assinatura_forjada(self):
        corpo = b'{"entry": []}'

        with pytest.raises(WhatsAppSignatureError, match="não confere"):
            gateway().verify_signature(corpo, "sha256=" + "0" * 64)

    def test_recusa_cabecalho_ausente(self):
        with pytest.raises(WhatsAppSignatureError, match="ausente"):
            gateway().verify_signature(b"{}", None)

    def test_recusa_cabecalho_em_formato_desconhecido(self):
        with pytest.raises(WhatsAppSignatureError):
            gateway().verify_signature(b"{}", "sha1=abc")

    def test_a_assinatura_muda_com_o_corpo(self):
        corpo = json.dumps(webhook_payload()).encode()
        assinatura = "sha256=" + hmac.new(SECRET.encode(), corpo, hashlib.sha256).hexdigest()

        with pytest.raises(WhatsAppSignatureError):
            gateway().verify_signature(corpo + b" ", assinatura)

    def test_sem_app_secret_a_checagem_e_pulada_com_aviso(self, caplog):
        with caplog.at_level("WARNING"):
            gateway(app_secret="").verify_signature(b"{}", None)

        assert any("produção" in r.message for r in caplog.records)


# ============================================================ leitura do payload
class TestLeituraDoPayload:
    def test_extrai_a_mensagem_de_texto_e_o_telefone(self):
        mensagens = WhatsAppCloudGateway.parse_webhook(
            webhook_payload("quero mudar de plano"))

        assert len(mensagens) == 1
        assert mensagens[0] == InboundWhatsAppMessage(
            wa_id="5511999990001", text="quero mudar de plano",
            message_id="wamid.ABC", profile_name="Maria", timestamp="1756500000")

    def test_ignora_o_que_nao_e_texto(self):
        assert WhatsAppCloudGateway.parse_webhook(webhook_payload(kind="image")) == []

    def test_ignora_confirmacao_de_entrega(self):
        payload = {"entry": [{"changes": [{"value": {
            "statuses": [{"id": "wamid.ABC", "status": "delivered"}]}}]}]}

        assert WhatsAppCloudGateway.parse_webhook(payload) == []

    def test_ignora_mensagem_de_texto_vazia(self):
        assert WhatsAppCloudGateway.parse_webhook(webhook_payload("   ")) == []

    def test_payload_desconhecido_nao_quebra(self):
        assert WhatsAppCloudGateway.parse_webhook({}) == []
        assert WhatsAppCloudGateway.parse_webhook({"entry": [{}]}) == []


# ===================================================================== envio
class TestEnvio:
    async def test_recusa_enviar_com_o_canal_desligado(self):
        with pytest.raises(RuntimeError, match="WHATSAPP_ENABLED"):
            await gateway(enabled=False).send("5511999990001", "oi")

    async def test_recusa_enviar_sem_credencial(self):
        with pytest.raises(RuntimeError):
            await gateway(access_token="").send("5511999990001", "oi")

    async def test_monta_o_corpo_no_formato_da_meta(self, monkeypatch):
        enviados: list[httpx.Request] = []

        class Transport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, req):
                enviados.append(req)
                return httpx.Response(200, json={"messages": [{"id": "wamid.OUT"}]},
                                      request=req)

        original = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient",
                            lambda *a, **kw: original(*a, **{**kw, "transport": Transport()}))

        resultado = await gateway().send("5511999990001", "Olá!")

        corpo = json.loads(enviados[0].content)
        assert resultado["messages"][0]["id"] == "wamid.OUT"
        assert corpo["messaging_product"] == "whatsapp"
        assert corpo["to"] == "5511999990001"
        assert corpo["text"]["body"] == "Olá!"
        assert enviados[0].headers["authorization"] == "Bearer EAAtoken"

    async def test_propaga_o_erro_da_meta_para_facilitar_o_diagnostico(self, monkeypatch):
        class Transport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, req):
                return httpx.Response(401, request=req, json={
                    "error": {"message": "Token expirado"}})

        original = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient",
                            lambda *a, **kw: original(*a, **{**kw, "transport": Transport()}))

        with pytest.raises(RuntimeError, match="Token expirado"):
            await gateway().send("5511999990001", "oi")


# ==================================================================== status
class TestStatus:
    def test_nunca_devolve_o_valor_de_um_segredo(self):
        status = gateway().status("https://exemplo.com")

        assert status["access_token"] == "configurado"
        assert status["verify_token"] == "configurado"
        assert "EAAtoken" not in json.dumps(status)
        assert SECRET not in json.dumps(status)

    def test_aponta_o_que_falta_configurar(self):
        status = gateway(access_token="", phone_number_id="").status("https://exemplo.com")

        assert status["can_send"] is False
        assert status["missing"]

    def test_mostra_a_url_exata_do_webhook(self):
        status = gateway().status("https://exemplo.com")

        assert status["webhook_url"] == \
            "https://exemplo.com/api/v1/channels/whatsapp/webhook"


# ================================================= o webhook dentro da API
class TestWebhookNaAPI:
    """O canal real ligado ao mesmo caso de uso de ingestão dos demais.

    É a prova de que "plugar um canal novo é escrever um adaptador": o webhook
    da Meta não conhece nada do núcleo além do comando de ingestão.
    """

    @pytest.fixture
    def cliente_com_canal_ligado(self, container, client):
        enviados: list[tuple[str, str]] = []

        class GatewayDeTeste(WhatsAppCloudGateway):
            async def send(self, to: str, text: str) -> dict:
                enviados.append((to, text))
                return {"messages": [{"id": "wamid.OUT"}]}

        container.whatsapp = GatewayDeTeste(WhatsAppSettings(
            enabled=True, phone_number_id="123456", access_token="EAAtoken",
            verify_token="token-verificacao", app_secret=SECRET))
        return client, enviados

    def test_handshake_devolve_o_desafio(self, cliente_com_canal_ligado):
        client, _ = cliente_com_canal_ligado

        response = client.get("/api/v1/channels/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": "token-verificacao",
            "hub.challenge": "desafio-123",
        })

        assert response.status_code == 200
        assert "desafio-123" in response.text

    def test_recusa_payload_sem_assinatura_valida(self, cliente_com_canal_ligado):
        client, _ = cliente_com_canal_ligado

        response = client.post("/api/v1/channels/whatsapp/webhook",
                               json=webhook_payload(),
                               headers={"X-Hub-Signature-256": "sha256=" + "0" * 64})

        assert response.status_code == 403

    def test_mensagem_assinada_vira_conversa_no_hub(self, cliente_com_canal_ligado):
        client, enviados = cliente_com_canal_ligado
        corpo = json.dumps(webhook_payload("quero mudar de plano")).encode()
        assinatura = "sha256=" + hmac.new(SECRET.encode(), corpo, hashlib.sha256).hexdigest()

        response = client.post("/api/v1/channels/whatsapp/webhook", content=corpo,
                               headers={"X-Hub-Signature-256": assinatura,
                                        "Content-Type": "application/json"})

        assert response.status_code == 200
        assert response.json() == {"received": 1}
        # a tarefa de fundo roda antes de o TestClient devolver o controle
        assert enviados and enviados[0][0] == "5511999990001"
        assert client.get("/api/v1/conversations").json()

    def test_envio_de_teste_funciona_com_o_canal_ligado(self, cliente_com_canal_ligado):
        client, enviados = cliente_com_canal_ligado

        response = client.post("/api/v1/channels/whatsapp/send",
                               json={"to": "5511999990001", "text": "Olá!"})

        assert response.status_code == 200
        assert enviados == [("5511999990001", "Olá!")]

    def test_status_confirma_que_o_canal_pode_enviar(self, cliente_com_canal_ligado):
        client, _ = cliente_com_canal_ligado

        status_body = client.get("/api/v1/channels/whatsapp/status").json()

        assert status_body["can_send"] is True
        assert status_body["signature_validation"] is True
        assert status_body["missing"] == []
