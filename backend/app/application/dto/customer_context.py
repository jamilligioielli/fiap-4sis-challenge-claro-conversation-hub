"""Visão consolidada de um cliente."""
from __future__ import annotations

from dataclasses import dataclass, field

from ...domain.entities.conversation import Conversation
from ...domain.entities.customer import Customer


@dataclass
class CustomerContext:
    customer: Customer
    conversations: list[Conversation] = field(default_factory=list)
    upgrade_options: list[dict] = field(default_factory=list)
