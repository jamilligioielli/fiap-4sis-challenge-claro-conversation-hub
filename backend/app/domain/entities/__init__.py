"""Entidades e agregados do domínio. Cada classe vive no seu próprio arquivo."""
from __future__ import annotations

from .conversation import Conversation
from .conversation_event import ConversationEvent
from .customer import Customer
from .handover import Handover
from .identifiers import new_id
from .message import Message
from .plan import Plan
from .session import Session
from .timeline_event import TimelineEvent

__all__ = [
    "Conversation", "ConversationEvent", "Customer", "Handover", "Message",
    "Plan", "Session", "TimelineEvent", "new_id",
]
