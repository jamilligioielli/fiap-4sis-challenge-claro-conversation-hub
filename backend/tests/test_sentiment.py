"""Melhoria 4 — humor do cliente detectado por regras."""
from __future__ import annotations

import pytest
from conftest import send

from app.domain.entities.conversation import Conversation
from app.domain.services.sentiment_detection_service import SentimentDetectionService
from app.domain.value_objects.sentiment import Sentiment

service = SentimentDetectionService()


class TestMensagemIsolada:
    @pytest.mark.parametrize("text", [
        "Já é a terceira vez que eu peço isso",
        "Que demora, ninguém resolve",
        "minha internet não funciona!!",
        "isso é um absurdo, vou no Procon",
        "quero falar com atendente",
        "não gostei do atendimento",
    ])
    def test_reclamacoes_sao_negativas(self, text):
        assert service.analyze(text).sentiment is Sentiment.negative

    @pytest.mark.parametrize("text", [
        "obrigado, ótimo", "Perfeito, muito obrigada!", "adorei, resolvido",
        "deu certo, valeu",
    ])
    def test_agradecimentos_sao_positivos(self, text):
        assert service.analyze(text).sentiment is Sentiment.positive

    @pytest.mark.parametrize("text", [
        "quero a segunda via da fatura", "qual o valor do plano de 50GB?", "", "oi",
    ])
    def test_pedidos_objetivos_sao_neutros(self, text):
        reading = service.analyze(text)
        assert reading.sentiment is Sentiment.neutral
        assert 0.4 <= reading.score <= 0.6

    def test_ignora_acento_e_caixa(self):
        assert service.analyze("PÉSSIMO").sentiment is Sentiment.negative
        assert service.analyze("pessimo").score == service.analyze("Péssimo").score

    def test_negacao_simples_inverte_a_palavra(self):
        assert service.analyze("não é ruim").score > 0.5
        assert service.analyze("não está bom").score < 0.5

    def test_expressao_composta_nao_conta_duas_vezes(self):
        """'muito obrigado' vale como expressão, não como expressão + 'obrigado'."""
        assert service.analyze("muito obrigado").score == pytest.approx(0.675)

    def test_indice_fica_entre_zero_e_um(self):
        pior = service.analyze("péssimo absurdo ridículo vergonha procon processar descaso")
        melhor = service.analyze("ótimo perfeito excelente adorei amei maravilha obrigado")
        assert pior.score == 0.0
        assert melhor.score == 1.0


class TestConversa:
    def test_sem_mensagens_e_neutra(self):
        reading = service.detect_with_score([])
        assert reading.sentiment is Sentiment.neutral and reading.score == 0.5

    def test_mensagens_recentes_pesam_mais(self):
        """Chegou irritado, foi bem atendido: não fica marcado como frustrado."""
        melhorou = service.detect_with_score([
            "que demora, terceira vez", "ok", "perfeito, muito obrigado", "adorei"])
        piorou = service.detect_with_score([
            "adorei", "ok", "que demora", "terceira vez, absurdo"])
        assert melhorou.sentiment is Sentiment.positive
        assert piorou.sentiment is Sentiment.negative

    def test_so_as_ultimas_cinco_contam(self):
        antigas = ["péssimo absurdo"] * 10
        recentes = ["obrigado, ótimo"] * 5
        assert service.detect(antigas + recentes) is Sentiment.positive

    def test_entidade_rejeita_indice_fora_da_faixa(self):
        conversation = Conversation(session_id="s", customer_id="c")
        with pytest.raises(ValueError):
            conversation.update_sentiment(Sentiment.positive, 1.5)
        conversation.update_sentiment(Sentiment.negative, 0.2)
        assert conversation.sentiment is Sentiment.negative


class TestDePontaAPonta:
    def test_reclamacao_marca_a_conversa_e_a_mensagem(self, client, carla):
        body = send(client, "whatsapp",
                    "Já é a terceira vez que reclamo da demora da internet", carla.id).json()

        assert body["sentiment"] == "negative"
        detalhe = client.get(f"/api/v1/conversations/{body['conversation_id']}").json()
        assert detalhe["sentiment"] == "negative"
        do_cliente = [m for m in detalhe["messages"] if m["author"] == "customer"]
        assert do_cliente[0]["sentiment"] == "negative"
        assert all(m["sentiment"] is None for m in detalhe["messages"]
                   if m["author"] != "customer")

    def test_atualiza_a_cada_mensagem_e_aparece_na_fila(self, client, maria):
        send(client, "web", "quero mudar de plano", maria.id)
        primeira = client.get("/api/v1/conversations").json()[0]
        assert primeira["sentiment"] == "neutral"

        send(client, "web", "perfeito, adorei, muito obrigada", maria.id)
        depois = client.get("/api/v1/conversations").json()[0]
        assert depois["sentiment"] == "positive"
        assert depois["sentiment_score"] > 0.6

    def test_continua_medindo_depois_do_transbordo(self, client, felipe):
        send(client, "whatsapp", "quero falar com atendente", felipe.id)
        body = send(client, "whatsapp", "que demora absurda, ninguém responde", felipe.id).json()

        assert body["reply"] == ""          # o bot continua calado
        assert body["sentiment"] == "negative"
