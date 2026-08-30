"""Adaptadores MongoDB do historico de longo prazo.

Indexados por customer_id: a memoria e do cliente, nao do canal. Modelo de
documentos porque o payload conversacional varia de forma por canal -- forcar
esse dado num schema relacional rigido custaria migracao a cada canal novo.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ...domain.entities import Conversation, Customer, Message
from ...domain.ports import (AuditLog, ConversationRepository, CustomerRepository,
                             StudioConfigRepository)
from ...domain.studio import StudioConfig

log = logging.getLogger("hub.mongo")


async def connect(url: str, db_name: str):
    """Devolve o handle do banco, ou None se indisponivel."""
    if not url:
        return None
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=2500)
        await client.admin.command("ping")
        db = client[db_name]
        await db.conversations.create_index("id", unique=True)
        await db.conversations.create_index("customer_id")
        await db.messages.create_index("conversation_id")
        await db.customers.create_index("id", unique=True)
        log.info("MongoDB conectado em %s", url)
        return db
    except Exception as exc:  # noqa: BLE001
        log.warning("MongoDB indisponível (%s) — histórico em memória", exc)
        return None


class MongoConversationRepository(ConversationRepository):
    def __init__(self, db) -> None:
        self._db = db

    async def get(self, conversation_id: str) -> Conversation | None:
        doc = await self._db.conversations.find_one({"id": conversation_id}, {"_id": 0})
        return Conversation(**doc) if doc else None

    async def save(self, conversation: Conversation) -> None:
        await self._db.conversations.update_one(
            {"id": conversation.id},
            {"$set": conversation.model_dump(mode="json")},
            upsert=True,
        )

    async def list(self, *, customer_id: str | None = None, area: str | None = None,
                   channel: str | None = None, status: str | None = None) -> list[Conversation]:
        query: dict = {}
        if customer_id:
            query["customer_id"] = customer_id
        if area:
            query["area"] = area
        if status:
            query["status"] = status
        if channel:
            query["channels_used"] = channel
        cursor = self._db.conversations.find(query, {"_id": 0}).sort("updated_at", -1)
        return [Conversation(**d) for d in await cursor.to_list(length=500)]

    async def open_for_customer(self, customer_id: str) -> Conversation | None:
        cursor = self._db.conversations.find(
            {"customer_id": customer_id, "status": {"$in": ["active", "waiting", "transferred"]}},
            {"_id": 0},
        ).sort("updated_at", -1).limit(1)
        docs = await cursor.to_list(length=1)
        return Conversation(**docs[0]) if docs else None

    async def add_message(self, message: Message) -> None:
        await self._db.messages.insert_one(message.model_dump(mode="json"))

    async def transcript(self, conversation_id: str) -> list[Message]:
        cursor = self._db.messages.find(
            {"conversation_id": conversation_id}, {"_id": 0}).sort("timestamp", 1)
        return [Message(**d) for d in await cursor.to_list(length=1000)]

    async def health(self) -> str:
        try:
            await self._db.command("ping")
            return "ok"
        except Exception:  # noqa: BLE001
            return "down"


class MongoCustomerRepository(CustomerRepository):
    def __init__(self, db) -> None:
        self._db = db

    async def get(self, customer_id: str) -> Customer | None:
        doc = await self._db.customers.find_one({"id": customer_id}, {"_id": 0})
        return Customer(**doc) if doc else None

    async def find_by_alias(self, channel: str, external_id: str) -> Customer | None:
        doc = await self._db.customers.find_one({f"aliases.{channel}": external_id}, {"_id": 0})
        return Customer(**doc) if doc else None

    async def save(self, customer: Customer) -> None:
        await self._db.customers.update_one(
            {"id": customer.id}, {"$set": customer.model_dump(mode="json")}, upsert=True)

    async def all(self) -> list[Customer]:
        cursor = self._db.customers.find({}, {"_id": 0})
        return [Customer(**d) for d in await cursor.to_list(length=500)]


class MongoStudioConfigRepository(StudioConfigRepository):
    KEY = {"_key": "studio-config"}

    def __init__(self, db, default: StudioConfig) -> None:
        self._db = db
        self._default = default

    async def get(self) -> StudioConfig:
        doc = await self._db.studio.find_one(self.KEY, {"_id": 0, "_key": 0})
        return StudioConfig(**doc) if doc else self._default

    async def save(self, config: StudioConfig) -> StudioConfig:
        config.updated_at = datetime.now(timezone.utc)
        await self._db.studio.update_one(
            self.KEY, {"$set": {**self.KEY, **config.model_dump(mode="json")}}, upsert=True)
        return config


class MongoAuditLog(AuditLog):
    def __init__(self, db) -> None:
        self._db = db

    async def record(self, action: str, customer_id: str | None, detail: dict) -> None:
        await self._db.audit.insert_one({
            "action": action, "customer_id": customer_id, "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    async def list(self, customer_id: str | None = None, limit: int = 50) -> list[dict]:
        query = {"customer_id": customer_id} if customer_id else {}
        cursor = self._db.audit.find(query, {"_id": 0}).sort("at", -1).limit(limit)
        return await cursor.to_list(length=limit)
