"""Porta do histórico de longo prazo das conversas."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..entities.conversation import Conversation
from ..entities.message import Message


class ConversationRepository(ABC):
    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    async def save(self, conversation: Conversation) -> None: ...

    @abstractmethod
    async def list(self, *, customer_id: str | None = None, area: str | None = None,
                   channel: str | None = None, status: str | None = None) -> list[Conversation]: ...

    @abstractmethod
    async def open_for_customer(self, customer_id: str) -> Conversation | None: ...

    @abstractmethod
    async def add_message(self, message: Message) -> None: ...

    @abstractmethod
    async def transcript(self, conversation_id: str) -> list[Message]: ...

    @abstractmethod
    async def health(self) -> str: ...
