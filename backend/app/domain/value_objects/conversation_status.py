"""Estado de uma conversa."""
from __future__ import annotations

from enum import Enum


class ConversationStatus(str, Enum):
    active = "active"
    waiting = "waiting"
    transferred = "transferred"
    pending = "pending"
