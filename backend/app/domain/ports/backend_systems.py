"""Porta dos sistemas internos da Claro."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BackendSystems(ABC):
    """Hoje atendida por serviços simulados; em produção, pelas integrações
    reais — sem alteração no núcleo."""

    @abstractmethod
    async def call(self, service: str, **kwargs) -> dict: ...

    @property
    @abstractmethod
    def available(self) -> list[str]: ...
