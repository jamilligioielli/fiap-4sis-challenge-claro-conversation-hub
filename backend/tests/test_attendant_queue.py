"""Melhoria 2 — fila do atendente humano: só transferidas, por prioridade."""
from __future__ import annotations

from datetime import timedelta

from conftest import send

from app.domain.entities.conversation import Conversation
from app.domain.services.attendance_queue import AttendanceQueue, QueueSort, waiting_seconds
from app.domain.value_objects.clock import utcnow
from app.domain.value_objects.priority import Priority

NOW = utcnow()


def _transferred(name: str, minutes_ago: int, priority: Priority = Priority.high,
                 agent: str | None = None) -> Conversation:
    conversation = Conversation(session_id="s", customer_id=name, customer_name=name)
    conversation.request_handover("teste", [], 1)
    conversation.handover.requested_at = NOW - timedelta(minutes=minutes_ago)
    conversation.priority = priority
    conversation.updated_at = NOW - timedelta(minutes=minutes_ago)
    if agent:
        conversation.assign_agent(agent)
    return conversation


class TestAttendanceQueue:
    queue = AttendanceQueue()

    def test_lista_vazia(self):
        assert self.queue.transferred([]) == []
        assert self.queue.sort([], QueueSort.priority, NOW) == []

    def test_so_entram_conversas_com_humano_e_em_curso(self):
        do_bot = Conversation(session_id="s", customer_id="bot")
        encerrada = _transferred("encerrada", 10)
        encerrada.close(closed_by="Ana")
        aberta = _transferred("aberta", 5)

        result = self.queue.transferred([do_bot, encerrada, aberta])

        assert [c.customer_id for c in result] == ["aberta"]

    def test_prioridade_primeiro_e_em_empate_quem_espera_mais(self):
        a = _transferred("alta-recente", 2)
        b = _transferred("alta-antiga", 40)
        c = _transferred("media-antiquissima", 90, Priority.medium)

        result = self.queue.sort([a, c, b], QueueSort.priority, NOW)

        assert [x.customer_id for x in result] == ["alta-antiga", "alta-recente",
                                                   "media-antiquissima"]

    def test_por_tempo_de_espera_ignora_a_prioridade_como_primeiro_criterio(self):
        a = _transferred("alta-recente", 2)
        c = _transferred("media-antiga", 90, Priority.medium)

        result = self.queue.sort([a, c], QueueSort.wait_time, NOW)

        assert [x.customer_id for x in result] == ["media-antiga", "alta-recente"]

    def test_filtra_pelo_atendente_mantendo_a_fila_sem_dono(self):
        minha = _transferred("minha", 5, agent="Ana")
        de_outro = _transferred("de-outro", 5, agent="Bruno")
        sem_dono = _transferred("sem-dono", 5)

        com_fila = self.queue.transferred([minha, de_outro, sem_dono], agent="Ana")
        so_minhas = self.queue.transferred([minha, de_outro, sem_dono], agent="Ana",
                                           include_unassigned=False)

        assert {c.customer_id for c in com_fila} == {"minha", "sem-dono"}
        assert [c.customer_id for c in so_minhas] == ["minha"]

    def test_tempo_de_espera_conta_desde_a_transferencia(self):
        assert waiting_seconds(_transferred("x", 3), NOW) == 180
        assert waiting_seconds(Conversation(session_id="s", customer_id="c"), NOW) is None


class TestEndpointFilaDoAtendente:
    def _transfer(self, client, customer_id: str) -> str:
        send(client, "whatsapp", "quero falar com atendente", customer_id)
        conversas = client.get(f"/api/v1/customers/{customer_id}/conversations").json()
        return conversas[0]["id"]

    def test_devolve_so_as_transferidas_com_tempo_de_espera(self, client, maria, felipe):
        send(client, "whatsapp", "quero a segunda via da fatura", maria.id)
        transferida = self._transfer(client, felipe.id)

        body = client.get("/api/v1/conversations?transferred_only=true").json()

        assert [c["id"] for c in body] == [transferida]
        assert body[0]["handover_requested_at"]
        assert body[0]["waiting_seconds"] >= 0
        assert body[0]["assigned_agent"] is None
        assert body[0]["attended_by"] == "agent"

    async def test_ordena_por_prioridade_e_tempo_de_espera(self, client, container, maria,
                                                           felipe):
        mais_antiga = self._transfer(client, felipe.id)
        mais_nova = self._transfer(client, maria.id)
        antiga = await container.conversations.get(mais_antiga)
        antiga.handover.requested_at = utcnow() - timedelta(minutes=30)
        await container.conversations.save(antiga)

        body = client.get("/api/v1/conversations?transferred_only=true").json()
        recentes = client.get(
            "/api/v1/conversations?transferred_only=true&sort_by=recent").json()

        assert [c["id"] for c in body] == [mais_antiga, mais_nova]
        assert recentes[0]["id"] == mais_nova

    def test_assumir_atribui_o_atendente_e_filtra_por_ele(self, client, maria, felipe):
        dele = self._transfer(client, felipe.id)
        sem_dono = self._transfer(client, maria.id)

        assumida = client.post(f"/api/v1/conversations/{dele}/handover",
                               json={"reason": "assumida", "agent": "Bruno"}).json()
        assert assumida["assigned_agent"] == "Bruno"

        da_ana = client.get(
            "/api/v1/conversations?transferred_only=true&agent=Ana").json()
        do_bruno_so = client.get(
            "/api/v1/conversations?transferred_only=true&agent=Bruno"
            "&include_unassigned=false").json()

        assert [c["id"] for c in da_ana] == [sem_dono]
        assert [c["id"] for c in do_bruno_so] == [dele]

    def test_registra_na_transcricao_quem_assumiu(self, client, felipe):
        conversa = self._transfer(client, felipe.id)
        client.post(f"/api/v1/conversations/{conversa}/handover",
                    json={"reason": "assumida", "agent": "Ana · CX"})

        textos = [m["text"] for m in client.get(f"/api/v1/conversations/{conversa}")
                  .json()["messages"]]
        assert "Ana · CX assumiu o atendimento" in textos

    def test_rejeita_criterio_de_ordenacao_invalido(self, client):
        assert client.get("/api/v1/conversations?sort_by=alfabetica").status_code == 422
