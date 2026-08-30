"""Servico de dominio: resolucao de identidade.

A regra que sustenta a continuidade entre canais: a memoria e indexada pelo
`customer_id`. O telefone do WhatsApp, o cookie do site e o device id do app sao
apelidos que resolvem para ele -- nunca a chave em si.

Sem esta regra, cada canal teria a sua propria sessao, e o cliente continuaria
percebendo "varias Claros".
"""
from __future__ import annotations

from ..entities import new_id
from ..ports import CustomerRepository, SessionRepository
from ..value_objects import Channel


class IdentityService:
    def __init__(self, sessions: SessionRepository, customers: CustomerRepository) -> None:
        self._sessions = sessions
        self._customers = customers

    async def resolve(self, channel: Channel, external_id: str | None,
                      customer_id: str | None) -> str:
        if customer_id:
            if external_id:
                await self._sessions.bind_alias(channel.value, external_id, customer_id)
            return customer_id

        if external_id:
            if cached := await self._sessions.resolve_alias(channel.value, external_id):
                return cached
            if known := await self._customers.find_by_alias(channel.value, external_id):
                await self._sessions.bind_alias(channel.value, external_id, known.id)
                return known.id

        return new_id("cust")
