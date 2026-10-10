"""Humor percebido do cliente numa mensagem ou numa conversa."""
from __future__ import annotations

from enum import Enum


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"

    @property
    def label(self) -> str:
        """Rótulo de operação, como o atendente lê na tela."""
        return {"positive": "Calmo", "neutral": "Neutro", "negative": "Frustrado"}[self.value]
