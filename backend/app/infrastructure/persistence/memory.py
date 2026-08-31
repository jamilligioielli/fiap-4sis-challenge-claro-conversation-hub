"""Adaptadores em memoria de todas as portas de persistencia.

Existem por dois motivos legitimos, nao por preguica:

  1. Testes de caso de uso rodam sem subir Redis nem MongoDB.
  2. A API sobe e funciona mesmo se a infraestrutura nao subir. Numa
     demonstracao com prazo, um container que nao levantou nao pode derrubar
     a apresentacao inteira -- o /health informa em que modo o hub esta.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ...domain.entities import Conversation, Customer, Message, Session
from ...domain.ports import (AuditLog, ConversationRepository, CustomerRepository,
                             SessionRepository, StudioConfigRepository)
from ...domain.studio import StudioConfig


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._aliases: dict[str, str] = {}

    async def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def save(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    async def resolve_alias(self, channel: str, external_id: str) -> str | None:
        return self._aliases.get(f"{channel}:{external_id}")

    async def bind_alias(self, channel: str, external_id: str, customer_id: str) -> None:
        self._aliases[f"{channel}:{external_id}"] = customer_id

    async def health(self) -> str:
        return "memory (fallback)"


class InMemoryConversationRepository(ConversationRepository):
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}

    async def get(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    async def save(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation

    async def list(self, *, customer_id: str | None = None, area: str | None = None,
                   channel: str | None = None, status: str | None = None) -> list[Conversation]:
        items = list(self._conversations.values())
        if customer_id:
            items = [c for c in items if c.customer_id == customer_id]
        if area:
            items = [c for c in items if c.area.value == area]
        if status:
            items = [c for c in items if c.status.value == status]
        if channel:
            items = [c for c in items if any(ch.value == channel for ch in c.channels_used)]
        return sorted(items, key=lambda c: c.updated_at, reverse=True)

    async def open_for_customer(self, customer_id: str) -> Conversation | None:
        candidates = [c for c in self._conversations.values()
                      if c.customer_id == customer_id and c.is_current]
        return sorted(candidates, key=lambda c: c.updated_at)[-1] if candidates else None

    async def add_message(self, message: Message) -> None:
        self._messages.setdefault(message.conversation_id, []).append(message)

    async def transcript(self, conversation_id: str) -> list[Message]:
        return sorted(self._messages.get(conversation_id, []), key=lambda m: m.timestamp)

    async def health(self) -> str:
        return "memory (fallback)"


class InMemoryCustomerRepository(CustomerRepository):
    def __init__(self) -> None:
        self._customers: dict[str, Customer] = {}

    async def get(self, customer_id: str) -> Customer | None:
        return self._customers.get(customer_id)

    async def find_by_alias(self, channel: str, external_id: str) -> Customer | None:
        return next((c for c in self._customers.values()
                     if c.aliases.get(channel) == external_id), None)

    async def save(self, customer: Customer) -> None:
        self._customers[customer.id] = customer

    async def all(self) -> list[Customer]:
        return list(self._customers.values())


class InMemoryStudioConfigRepository(StudioConfigRepository):
    """Guarda a configuração da persona em memória.

    Entrega e guarda cópias em vez do próprio objeto. Sem isso, quem chamasse
    `get()` receberia a instância interna do repositório e poderia alterá-la sem
    passar por `save()` — o que dá uma gravação silenciosa, sem incremento de
    versão e sem trilha de auditoria. Como o padrão de fábrica é um objeto de
    módulo, a mesma referência ainda contaminaria toda instância criada depois.
    """

    def __init__(self, default: StudioConfig | None = None) -> None:
        self._config = (default or StudioConfig()).model_copy(deep=True)

    async def get(self) -> StudioConfig:
        return self._config.model_copy(deep=True)

    async def save(self, config: StudioConfig) -> StudioConfig:
        config.updated_at = datetime.now(timezone.utc)
        self._config = config.model_copy(deep=True)
        return config


class InMemoryAuditLog(AuditLog):
    def __init__(self) -> None:
        self._entries: list[dict] = []

    async def record(self, action: str, customer_id: str | None, detail: dict) -> None:
        self._entries.append({
            "action": action, "customer_id": customer_id, "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    async def list(self, customer_id: str | None = None, limit: int = 50) -> list[dict]:
        items = self._entries
        if customer_id:
            items = [e for e in items if e["customer_id"] == customer_id]
        return list(reversed(items[-limit:]))
