"""Resposta do cliente quando o assistente pergunta se ele quer continuar o
assunto anterior ao mudar de canal."""
from __future__ import annotations

from enum import Enum


class ContextDecision(str, Enum):
    continue_previous = "continue_previous"
    start_new = "start_new"
    unclear = "unclear"
