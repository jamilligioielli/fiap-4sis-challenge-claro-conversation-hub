"""Melhoria 1 — NPS do atendimento automatizado versus o humano."""
from __future__ import annotations

from conftest import send

from app.domain.entities.conversation import Conversation
from app.domain.entities.nps_survey import NpsSurvey
from app.domain.services.nps_analytics_service import NpsAnalyticsService


def _conversation(score: int | None, *, human: bool = False, closed_by: str = "bot",
                  dismissed: bool = False, agent_replies: int = 0) -> Conversation:
    conversation = Conversation(session_id="s", customer_id="c")
    if human:
        conversation.request_handover("teste", [], 1)
    conversation.agent_replies = agent_replies
    survey = NpsSurvey(closed_by=closed_by, dismissed=dismissed)
    if score is not None:
        survey.record(score)
    conversation.nps = survey
    return conversation


# =============================================================== serviço
class TestNpsAnalyticsService:
    service = NpsAnalyticsService()

    def test_lista_vazia_devolve_grupos_zerados(self):
        result = self.service.calculate_bot_vs_agent_nps([])

        assert result.bot.total == 0
        assert result.bot.average_score is None
        assert result.agent.nps is None
        assert result.score_difference is None
        assert result.agent_better is None

    def test_separa_notas_do_bot_e_do_humano(self):
        conversations = [
            _conversation(10), _conversation(6), _conversation(8),          # bot
            _conversation(9, human=True), _conversation(10, human=True),   # humano
        ]

        result = self.service.calculate_bot_vs_agent_nps(conversations)

        assert result.bot.total == 3
        assert result.bot.average_score == 8.0
        assert (result.bot.promoters, result.bot.passives, result.bot.detractors) == (1, 1, 1)
        assert result.bot.nps == 0.0
        assert result.agent.total == 2
        assert result.agent.average_score == 9.5
        assert result.agent.nps == 100.0
        assert result.score_difference == 1.5
        assert result.agent_better is True
        assert result.overall.total == 5

    def test_usa_as_mesmas_faixas_do_kpi_de_nps(self):
        """6 é detrator, 7 e 8 neutros, 9 e 10 promotores."""
        result = self.service.calculate_bot_vs_agent_nps(
            [_conversation(s) for s in (6, 7, 8, 9)])

        assert result.bot.detractors == 1
        assert result.bot.passives == 2
        assert result.bot.promoters == 1
        assert result.bot.percentages == {"promoters": 25.0, "passives": 50.0,
                                          "detractors": 25.0}

    def test_pesquisa_sem_nota_nao_entra_na_media_mas_e_contada(self):
        result = self.service.calculate_bot_vs_agent_nps([
            _conversation(9), _conversation(None, dismissed=True), _conversation(None),
        ])

        assert result.bot.total == 1
        assert result.bot.average_score == 9.0
        assert result.bot.surveys_sent == 3
        assert result.bot.unanswered == 2

    def test_so_bot_deixa_o_lado_humano_vazio(self):
        result = self.service.calculate_bot_vs_agent_nps([_conversation(9), _conversation(3)])

        assert result.agent.total == 0
        assert result.agent.average_score is None
        assert result.score_difference is None

    def test_conta_como_humano_quem_foi_encerrado_ou_respondido_por_atendente(self):
        """Sem transferência formal, o atendente ainda pode ter atendido."""
        encerrada_no_console = _conversation(4, closed_by="Admin CX")
        respondida_no_console = _conversation(5, agent_replies=2)

        result = self.service.calculate_bot_vs_agent_nps(
            [encerrada_no_console, respondida_no_console])

        assert result.agent.total == 2
        assert result.bot.total == 0


# ================================================================ entidade
class TestQuemAtendeu:
    def test_conversa_sem_humano_e_do_bot(self):
        assert Conversation(session_id="s", customer_id="c").attended_by == "bot"

    def test_transferencia_torna_o_atendimento_humano(self):
        conversation = Conversation(session_id="s", customer_id="c")
        conversation.request_handover("pediu atendente", [], 2)
        assert conversation.attended_by == "agent"

    def test_resposta_do_atendente_conta(self):
        conversation = Conversation(session_id="s", customer_id="c")
        conversation.register_agent_reply()
        assert conversation.agent_replies == 1
        assert conversation.attended_by == "agent"

    def test_documento_antigo_sem_os_campos_novos_continua_carregando(self):
        legado = {"id": "conv_x", "session_id": "s", "customer_id": "c"}
        conversation = Conversation(**legado)
        assert conversation.agent_replies == 0
        assert conversation.sentiment is None


# ===================================================================== API
class TestEndpointComparativo:
    def test_responde_vazio_sem_conversas(self, client):
        body = client.get("/api/v1/dashboard/nps-comparison").json()

        assert body["area"] == "Todos"
        assert body["bot"]["total"] == 0
        assert body["agent"]["average_score"] is None
        assert body["comparison"]["agent_better"] is None

    async def test_separa_bot_e_atendente_de_ponta_a_ponta(self, client, container, maria,
                                                           felipe):
        # Maria: o assistente atende e encerra; nota 10.
        send(client, "whatsapp", "quero a segunda via da fatura", maria.id)
        send(client, "whatsapp", "obrigada, era só isso", maria.id)
        send(client, "whatsapp", "10", maria.id)

        # Felipe: transferido para humano; atendente encerra; nota 4.
        send(client, "whatsapp", "quero falar com atendente", felipe.id)
        conversa = (await container.conversations.list(customer_id=felipe.id))[0]
        client.post(f"/api/v1/conversations/{conversa.id}/messages",
                    json={"text": "Oi, Felipe, estou com o seu caso."})
        client.post(f"/api/v1/conversations/{conversa.id}/close",
                    json={"agent": "Ana · CX", "survey": True})
        send(client, "whatsapp", "4", felipe.id)

        body = client.get("/api/v1/dashboard/nps-comparison").json()

        assert body["bot"]["total"] == 1 and body["bot"]["average_score"] == 10.0
        assert body["agent"]["total"] == 1 and body["agent"]["average_score"] == 4.0
        assert body["comparison"]["score_difference"] == -6.0
        assert body["comparison"]["agent_better"] is False

    def test_respeita_o_filtro_de_area(self, client, maria):
        send(client, "whatsapp", "quero a segunda via da fatura", maria.id)
        send(client, "whatsapp", "obrigada, era só isso", maria.id)
        send(client, "whatsapp", "9", maria.id)

        financeiro = client.get("/api/v1/dashboard/nps-comparison?area=Financeiro").json()
        vendas = client.get("/api/v1/dashboard/nps-comparison?area=Vendas").json()

        assert financeiro["bot"]["total"] == 1
        assert vendas["bot"]["total"] == 0
        assert vendas["area"] == "Vendas"


class TestTaxaDeResolucao:
    def test_conta_encerradas_sem_humano(self, client, maria, felipe):
        # resolvida pelo bot
        send(client, "whatsapp", "quero a segunda via da fatura", maria.id)
        send(client, "whatsapp", "obrigada, era só isso", maria.id)
        # transferida: não é resolução digital
        send(client, "whatsapp", "quero falar com atendente", felipe.id)

        body = client.get("/api/v1/dashboard").json()

        assert body["resolution_rate"]["value"] == 50.0
        assert body["handover_rate"]["value"] == 50.0
