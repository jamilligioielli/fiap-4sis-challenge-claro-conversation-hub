"""Espera o cliente terminar de escrever antes de responder.

Gente não escreve um parágrafo e aperta enviar. Gente manda "oi, tudo bem?",
depois "queria ver meu plano", depois "é que a franquia acabou de novo". Um
assistente que responde à primeira já está atrasado nas outras duas — e o
cliente recebe três respostas para um pedido só.

A solução é uma janela de silêncio: cada mensagem reinicia um cronômetro, e o
hub só processa quando o cliente para. As mensagens do intervalo chegam juntas,
como um pedido só, que é como elas foram pensadas.

O buffer vive em memória do processo. Numa instalação com várias réplicas isso
exigiria estado compartilhado (o Redis já está lá para isso), mas seria preciso
também garantir que as mensagens de um mesmo cliente caiam sempre na mesma
réplica. Fora do escopo do MVP, e registrado aqui para não virar surpresa.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

log = logging.getLogger("hub.debounce")


@dataclass
class _Pending:
    """Mensagens acumuladas de um cliente e o cronômetro em curso."""
    texts: list[str] = field(default_factory=list)
    waiter: asyncio.Event = field(default_factory=asyncio.Event)
    superseded: bool = False


class MessageDebouncer:
    """Agrupa mensagens seguidas do mesmo cliente numa só rodada.

    `submit` devolve o texto acumulado quando a janela fecha, ou `None` quando
    outra mensagem chegou antes e assumiu o lote — nesse caso quem responde é a
    chamada mais recente, e esta se retira em silêncio.
    """

    def __init__(self, window_seconds: float) -> None:
        self._window = max(0.0, window_seconds)
        self._pending: dict[str, _Pending] = {}
        self._lock = asyncio.Lock()

    @property
    def window_seconds(self) -> float:
        return self._window

    async def submit(self, key: str, text: str) -> str | None:
        if self._window <= 0:
            return text

        async with self._lock:
            entry = self._pending.get(key)
            if entry is not None:
                # Chegou mensagem nova antes de a janela fechar: o lote passa
                # para esta chamada e a anterior se aposenta.
                entry.superseded = True
                entry.waiter.set()
                textos = [*entry.texts, text]
            else:
                textos = [text]
            atual = _Pending(texts=textos)
            self._pending[key] = atual

        try:
            await asyncio.wait_for(atual.waiter.wait(), timeout=self._window)
        except asyncio.TimeoutError:
            pass  # silêncio pelo tempo da janela: é a nossa vez de responder

        async with self._lock:
            if atual.superseded:
                return None
            self._pending.pop(key, None)

        if len(atual.texts) > 1:
            log.info("Agrupadas %d mensagens de %s numa só rodada",
                     len(atual.texts), key[-6:])
        return "\n".join(atual.texts)

    async def flush(self, key: str) -> None:
        """Descarta o lote em curso — usado quando a conversa muda de estado
        por fora (o atendente assume, a conversa é encerrada)."""
        async with self._lock:
            if (entry := self._pending.pop(key, None)) is not None:
                entry.superseded = True
                entry.waiter.set()
