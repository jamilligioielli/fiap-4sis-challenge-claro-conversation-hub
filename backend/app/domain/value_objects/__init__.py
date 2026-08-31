"""Objetos de valor do domínio.

São imutáveis, não têm identidade e não dependem de framework, banco ou HTTP.
Este módulo apenas reexporta — cada classe vive no seu próprio arquivo.
"""
from __future__ import annotations

from .area import Area
from .author import Author
from .channel import Channel
from .clock import utcnow
from .consent import Consent
from .context_decision import ContextDecision
from .conversation_status import ConversationStatus
from .intent import Intent
from .intent_engine import IntentEngine
from .priority import Priority
from .response_source import ResponseSource
from .unidentified_intent import UNIDENTIFIED

__all__ = [
    "Area", "Author", "Channel", "Consent", "ContextDecision", "ConversationStatus",
    "Intent", "IntentEngine", "Priority", "ResponseSource", "UNIDENTIFIED", "utcnow",
]
