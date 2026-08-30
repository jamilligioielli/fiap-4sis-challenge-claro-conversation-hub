"""Adaptador Redis do contexto de sessao (curto prazo).

A sessao tem TTL: contexto de conversa nao e memoria permanente. O que precisa
sobreviver ao TTL ja foi gravado no historico de longo prazo pelo repositorio
de conversas -- os dois niveis existem justamente porque tem finalidades
diferentes.
"""
from __future__ import annotations

import json
import logging

from ...domain.entities import Session
from ...domain.ports import SessionRepository

log = logging.getLogger("hub.redis")

SESSION_KEY = "hub:session:{sid}"
ALIAS_KEY = "hub:alias:{channel}:{external_id}"
ALIAS_TTL = 60 * 60 * 24 * 30  # 30 dias


class RedisSessionRepository(SessionRepository):
    def __init__(self, client, ttl_seconds: int) -> None:
        self._redis = client
        self._ttl = ttl_seconds

    @classmethod
    async def connect(cls, url: str, ttl_seconds: int) -> "RedisSessionRepository | None":
        if not url:
            return None
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(url, decode_responses=True)
            await client.ping()
            log.info("Redis conectado em %s", url)
            return cls(client, ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            log.warning("Redis indisponível (%s) — contexto de sessão em memória", exc)
            return None

    async def get(self, session_id: str) -> Session | None:
        raw = await self._redis.get(SESSION_KEY.format(sid=session_id))
        return Session(**json.loads(raw)) if raw else None

    async def save(self, session: Session) -> None:
        await self._redis.set(
            SESSION_KEY.format(sid=session.session_id),
            session.model_dump_json(), ex=self._ttl,
        )

    async def resolve_alias(self, channel: str, external_id: str) -> str | None:
        return await self._redis.get(ALIAS_KEY.format(channel=channel, external_id=external_id))

    async def bind_alias(self, channel: str, external_id: str, customer_id: str) -> None:
        await self._redis.set(
            ALIAS_KEY.format(channel=channel, external_id=external_id),
            customer_id, ex=ALIAS_TTL,
        )

    async def health(self) -> str:
        try:
            await self._redis.ping()
            return "ok"
        except Exception:  # noqa: BLE001
            return "down"

    async def close(self) -> None:
        await self._redis.aclose()
