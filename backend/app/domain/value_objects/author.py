"""Quem escreveu uma mensagem."""
from __future__ import annotations

from enum import Enum


class Author(str, Enum):
    customer = "customer"
    bot = "bot"
    agent = "agent"
    system = "system"
