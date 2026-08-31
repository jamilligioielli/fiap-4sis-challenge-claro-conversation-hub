"""Porta do contexto de curto prazo."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..entities.session import Session


class SessionRepository(ABC):
    @abstractmethod
    async def get(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def save(self, session: Session) -> None: ...

    @abstractmethod
    async def resolve_alias(self, channel: str, external_id: str) -> str | None: ...

    @abstractmethod
    async def bind_alias(self, channel: str, external_id: str, customer_id: str) -> None: ...

    @abstractmethod
    async def health(self) -> str: ...
