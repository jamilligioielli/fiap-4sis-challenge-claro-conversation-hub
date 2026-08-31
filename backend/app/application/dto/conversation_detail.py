"""Conversa completa com o painel de apoio ao atendente."""
from __future__ import annotations

from dataclasses import dataclass, field

from ...domain.entities.conversation import Conversation
from ...domain.entities.message import Message


@dataclass
class ConversationDetail:
    conversation: Conversation
    messages: list[Message]
    summary: dict[str, str] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    insights: list[dict] = field(default_factory=list)
