"""Origem do texto de uma resposta do assistente.

Distinguir os dois importa: a interface mostra qual gerou, e ninguém precisa
acreditar na palavra do sistema sobre estar ou não usando IA generativa.
"""
from __future__ import annotations

from enum import Enum


class ResponseSource(str, Enum):
    generative = "generative"
    template = "template"

    @property
    def label(self) -> str:
        return {"generative": "IA generativa", "template": "modelo de texto"}[self.value]
