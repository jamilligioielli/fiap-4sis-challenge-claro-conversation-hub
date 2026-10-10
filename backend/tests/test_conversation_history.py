"""Melhoria 5 — linha do tempo das conversas do cliente."""
from __future__ import annotations

from datetime import timedelta

from conftest import send

from app.domain.entities.conversation import Conversation
from app.domain.entities.nps_survey import NpsSurvey
from app.domain.services.conversation_insights_service import (ConversationInsightsService,
                                                              HistoryStatus, history_status,
                                                              history_type)
from app.domain.value_objects.area import Area
from app.domain.value_objects.clock import utcnow
from app.domain.value_objects.intent import Intent

NOW = utcnow()


def _past(days_ago: int, area: Area = Area.suporte, score: int | None = None,
          closed: bool = True, customer_id: str = "c") -> Conversation:
    conversation = Conversation(session_id="s", customer_id=customer_id, area=area,
                                started_at=NOW - timedelta(days=days_ago))
    if closed:
        conversation.close(with_survey=score is not None)
    if score is not None:
        conversation.nps = NpsSurvey()
        conversation.record_nps(score)
    return conversation


class TestSituacaoETipo:
    def test_em_curso_resolvida_e_insatisfeita(self):
        assert history_status(_past(1, closed=False)) is HistoryStatus.open
        assert history_status(_past(1)) is HistoryStatus.resolved
        assert history_status(_past(1, score=9)) is HistoryStatus.resolved
        assert history_status(_past(1, score=3)) is HistoryStatus.unresolved

    def test_tipo_deriva_da_area_e_consulta_da_intencao(self):
        assert history_type(_past(1, Area.retencao)) == ("cancelamento", "Cancelamento")
        assert history_type(_past(1, Area.tecnico)) == ("suporte", "Suporte")
        consulta = _past(1, Area.vendas)
        consulta.intent = Intent(slug="consulta_informacao", name="Consulta de Informação",
                                 confidence=0.9, area=Area.vendas)
        assert history_type(consulta) == ("consulta", "Consulta")


class TestInsights:
    service = ConversationInsightsService()

    def test_sem_conversas(self):
        insights = self.service.calculate_insights([])
        assert insights.total_conversations == 0
        assert insights.average_frequency_days is None
        assert insights.resolution_rate is None

    def test_uma_conversa_nao_tem_frequencia(self):
        insights = self.service.calculate_insights([_past(3, score=8)])
        assert insights.total_conversations == 1
        assert insights.average_frequency_days is None
        assert insights.average_nps == 8.0
        assert insights.average_nps_category == "neutro"

    def test_calcula_frequencia_tipo_nps_e_resolucao(self):
        conversas = [
            _past(30, Area.suporte, score=9),
            _past(20, Area.suporte, score=3),
            _past(10, Area.vendas, score=9),
            _past(0, Area.suporte, closed=False),
        ]

        insights = self.service.calculate_insights(conversas)

        assert insights.total_conversations == 4
        assert insights.average_frequency_days == 10.0
        assert insights.most_common_type == "suporte"
        assert insights.average_nps == 7.0
        assert insights.closed_conversations == 3
        assert insights.resolution_rate == 66.7


class TestEndpointHistorico:
    def test_cliente_inexistente_e_404(self, client):
        assert client.get("/api/v1/customers/ninguem/conversation-history").status_code == 404

    def test_cliente_sem_conversas_devolve_lista_vazia(self, client, juliana):
        body = client.get(f"/api/v1/customers/{juliana.id}/conversation-history").json()

        assert body["items"] == []
        assert body["insights"]["total_conversations"] == 0

    async def test_devolve_as_mais_recentes_primeiro_dentro_da_janela(self, client, container,
                                                                      maria):
        for days in (400, 90, 40, 5):
            await container.conversations.save(
                _past(days, Area.suporte, score=9, customer_id=maria.id))

        body = client.get(f"/api/v1/customers/{maria.id}/conversation-history?months=6").json()

        dias = [item["date"] for item in body["items"]]
        assert len(dias) == 3                          # a de 400 dias ficou de fora
        assert dias == sorted(dias, reverse=True)
        assert body["insights"]["total_conversations"] == 3
        assert body["items"][0]["status"] == "resolved"
        assert body["items"][0]["nps_category"] == "promotor"

    async def test_respeita_o_limite(self, client, container, maria):
        for days in range(1, 10):
            await container.conversations.save(_past(days, customer_id=maria.id))

        body = client.get(f"/api/v1/customers/{maria.id}/conversation-history").json()

        assert len(body["items"]) == 6
        assert body["insights"]["total_conversations"] == 9

    def test_conversa_real_aparece_como_atual_e_abre_a_transcricao(self, client, maria):
        conversa = send(client, "web", "quero a segunda via da fatura", maria.id).json()

        body = client.get(f"/api/v1/customers/{maria.id}/conversation-history").json()

        item = body["items"][0]
        assert item["id"] == conversa["conversation_id"]
        assert item["current"] is True
        assert item["status"] == "open"
        assert item["type"] == "financeiro"
        assert item["message_count"] >= 2
        transcricao = client.get(f"/api/v1/conversations/{item['id']}").json()["messages"]
        assert len(transcricao) == item["message_count"]
