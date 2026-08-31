"""Testes da janela de silêncio antes de o assistente responder.

Gente manda "oi, tudo bem?" e só depois o pedido de verdade. Responder à
primeira é responder cedo demais — e devolver três respostas para um pedido só.

A janela usada aqui é de milissegundos: o comportamento a verificar é o
agrupamento, não a duração. Trinta segundos por asserção transformaria a suíte
numa vigília.
"""
from __future__ import annotations

import asyncio

import pytest

from app.infrastructure.buffering.message_debouncer import MessageDebouncer

JANELA = 0.12


@pytest.fixture
def debouncer() -> MessageDebouncer:
    return MessageDebouncer(JANELA)


class TestAgrupamento:
    async def test_mensagem_sozinha_passa_depois_da_janela(self, debouncer):
        assert await debouncer.submit("cus1", "quero mudar de plano") == "quero mudar de plano"

    async def test_duas_mensagens_seguidas_viram_um_pedido_so(self, debouncer):
        primeira = asyncio.create_task(debouncer.submit("cus1", "oi, tudo bem?"))
        await asyncio.sleep(JANELA / 3)
        segunda = asyncio.create_task(debouncer.submit("cus1", "queria ver meu plano"))

        assert await primeira is None, "a primeira cede a vez para a mais recente"
        assert await segunda == "oi, tudo bem?\nqueria ver meu plano"

    async def test_a_janela_reinicia_a_cada_mensagem(self, debouncer):
        """Três mensagens picadas continuam sendo um pedido só."""
        tarefas = []
        for texto in ("oi", "tudo bem?", "queria ver minha fatura"):
            tarefas.append(asyncio.create_task(debouncer.submit("cus1", texto)))
            await asyncio.sleep(JANELA / 3)

        resultados = await asyncio.gather(*tarefas)

        assert resultados[:2] == [None, None]
        assert resultados[-1] == "oi\ntudo bem?\nqueria ver minha fatura"

    async def test_mensagens_separadas_pela_janela_sao_pedidos_distintos(self, debouncer):
        primeira = await debouncer.submit("cus1", "quero mudar de plano")
        segunda = await debouncer.submit("cus1", "e a minha fatura?")

        assert primeira == "quero mudar de plano"
        assert segunda == "e a minha fatura?"

    async def test_clientes_diferentes_nao_se_misturam(self, debouncer):
        maria = asyncio.create_task(debouncer.submit("cus_maria", "quero mais internet"))
        joao = asyncio.create_task(debouncer.submit("cus_joao", "quero minha fatura"))

        assert await maria == "quero mais internet"
        assert await joao == "quero minha fatura"


class TestJanelaDesligada:
    async def test_janela_zero_responde_na_hora(self):
        """É assim que a suíte inteira roda, e é a configuração para gravar."""
        debouncer = MessageDebouncer(0)

        assert await debouncer.submit("cus1", "oi") == "oi"

    async def test_janela_negativa_e_tratada_como_zero(self):
        assert MessageDebouncer(-5).window_seconds == 0


class TestDescarte:
    async def test_flush_libera_o_lote_em_espera_sem_resposta(self, debouncer):
        """Quando o atendente encerra, o lote em espera perde o sentido:
        seria responder a um atendimento que já acabou."""
        pendente = asyncio.create_task(debouncer.submit("cus1", "e aí?"))
        await asyncio.sleep(JANELA / 3)

        await debouncer.flush("cus1")

        assert await pendente is None

    async def test_flush_de_cliente_sem_lote_nao_quebra(self, debouncer):
        await debouncer.flush("cus_sem_nada")  # não levanta


class TestConfiguracao:
    def test_a_janela_vem_do_ambiente(self, monkeypatch):
        import importlib

        import app.settings as settings
        monkeypatch.setenv("BOT_REPLY_DELAY_SECONDS", "8")
        importlib.reload(settings)

        assert settings.ConversationSettings().reply_delay_seconds == 8.0

        monkeypatch.delenv("BOT_REPLY_DELAY_SECONDS")
        importlib.reload(settings)

    def test_o_padrao_de_producao_e_trinta_segundos(self, monkeypatch):
        import importlib

        import app.settings as settings
        monkeypatch.delenv("BOT_REPLY_DELAY_SECONDS", raising=False)
        importlib.reload(settings)

        assert settings.ConversationSettings().reply_delay_seconds == 30.0
