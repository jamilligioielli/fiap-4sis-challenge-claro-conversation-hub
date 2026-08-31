"""Porta da trilha de auditoria de acesso a dado pessoal."""
from __future__ import annotations

from abc import ABC, abstractmethod


class AuditLog(ABC):
    @abstractmethod
    async def record(self, action: str, customer_id: str | None, detail: dict) -> None: ...

    @abstractmethod
    async def list(self, customer_id: str | None = None, limit: int = 50) -> list[dict]: ...
