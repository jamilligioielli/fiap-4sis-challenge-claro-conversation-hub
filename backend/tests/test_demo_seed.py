"""Dados de demonstração da Sprint 4: opcionais, idempotentes e coerentes."""
from __future__ import annotations

from app.infrastructure.demo_seed import CLOSED, DEMO_PREFIX, WAITING, populate_demo


async def test_cria_uma_vez_so(container):
    primeira = await populate_demo(container.customers, container.conversations)
    segunda = await populate_demo(container.customers, container.conversations)

    assert primeira == len(CLOSED) + len(WAITING)
    assert segunda == 0
    todas = await container.conversations.list()
    assert all(c.id.startswith(DEMO_PREFIX) for c in todas)


async def test_painel_sem_demo_continua_vazio(client):
    assert client.get("/api/v1/dashboard").json()["has_data"] is False


async def test_alimenta_as_cinco_melhorias(client, container, maria):
    await populate_demo(container.customers, container.conversations)

    nps = client.get("/api/v1/dashboard/nps-comparison").json()
    assert nps["bot"]["total"] > 0 and nps["agent"]["total"] > 0
    assert nps["comparison"]["agent_better"] is True

    fila = client.get("/api/v1/conversations?transferred_only=true").json()
    assert len(fila) == len(WAITING)
    assert [c["priority"] for c in fila] == sorted(
        (c["priority"] for c in fila), key=["high", "medium", "low"].index)
    assert {c["sentiment"] for c in fila} >= {"negative", "positive"}

    historico = client.get(f"/api/v1/customers/{maria.id}/conversation-history").json()
    assert len(historico["items"]) == 6
    assert historico["insights"]["average_frequency_days"] > 0
    assert {i["status"] for i in historico["items"]} >= {"resolved", "unresolved"}


async def test_cada_cliente_tem_no_maximo_uma_conversa_vigente(container):
    await populate_demo(container.customers, container.conversations)

    for customer in await container.customers.all():
        vigentes = [c for c in await container.conversations.list(customer_id=customer.id)
                    if c.is_current]
        assert len(vigentes) <= 1, customer.id


async def test_simulador_continua_a_conversa_transferida_em_silencio(client, container, felipe):
    """Depois do seed, o cliente que escreve cai na conversa que já está com humano."""
    await populate_demo(container.customers, container.conversations)
    from conftest import send

    body = send(client, "whatsapp", "alô? ainda estou esperando", felipe.id).json()

    assert body["conversation_id"] == f"{DEMO_PREFIX}w1"
    assert body["reply"] == ""
