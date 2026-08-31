"""Encadeia um classificador primário e o seu reserva."""
from __future__ import annotations

import logging

from ...domain.ports.intent_classifier import IntentClassifier
from ...domain.value_objects.intent import Intent

log = logging.getLogger("hub.intent")


class ResilientIntentClassifier(IntentClassifier):
    def __init__(self, primary: IntentClassifier, fallback: IntentClassifier) -> None:
        self._primary = primary
        self._fallback = fallback
        self.last_engine = fallback.engine_name

    @property
    def engine_name(self) -> str:
        return f"{self._primary.engine_name} → {self._fallback.engine_name}"

    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent:
        try:
            intent = await self._primary.classify(text, history=history)
            self.last_engine = self._primary.engine_name
            return intent
        except Exception as exc:  # noqa: BLE001
            log.warning("Classificador primário indisponível (%s) — usando regras", exc)
            self.last_engine = self._fallback.engine_name
            return await self._fallback.classify(text, history=history)
