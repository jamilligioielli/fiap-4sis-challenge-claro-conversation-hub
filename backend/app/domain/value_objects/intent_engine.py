"""Motor que classificou a intenção."""
from __future__ import annotations

from enum import Enum


class IntentEngine(str, Enum):
    llm = "llm"
    rules = "rules"
