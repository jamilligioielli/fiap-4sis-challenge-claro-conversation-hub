"""Porta da configuração da persona."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..studio.studio_config import StudioConfig


class StudioConfigRepository(ABC):
    @abstractmethod
    async def get(self) -> StudioConfig: ...

    @abstractmethod
    async def save(self, config: StudioConfig) -> StudioConfig: ...
