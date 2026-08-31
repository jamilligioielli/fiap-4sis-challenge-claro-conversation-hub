"""Porta de classificação de intenção."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..value_objects.intent import Intent


class IntentClassifier(ABC):
    """O caso de uso não sabe se atrás disto há um modelo de linguagem ou um
    classificador por palavra-chave."""

    @abstractmethod
    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent: ...

    @property
    @abstractmethod
    def engine_name(self) -> str: ...
