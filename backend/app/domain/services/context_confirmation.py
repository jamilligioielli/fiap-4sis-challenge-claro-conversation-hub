"""Interpretação da resposta do cliente à pergunta de continuidade.

Ao mudar de canal, o assistente pergunta se o cliente quer retomar o assunto
anterior. Presumir a resposta seria repetir, do lado oposto, o erro que a solução
existe para corrigir: decidir pelo cliente o que ele quer.
"""
from __future__ import annotations

import unicodedata

from ..value_objects.context_decision import ContextDecision

CONTINUE = (
    "sim", "continuar", "continua", "isso", "esse mesmo", "esse assunto", "quero sim",
    "pode continuar", "seguir", "prosseguir", "e sobre isso", "e isso mesmo", "claro",
    "por favor", "exato", "aquele", "o mesmo",
)

START_NEW = (
    "nao", "outro", "outra coisa", "novo assunto", "e outro", "diferente",
    "nada a ver", "mudar de assunto", "esquece", "deixa pra la", "outro assunto",
)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower().strip(" .!?,"))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class ContextConfirmationService:
    """Decide se a mensagem do cliente confirma, recusa ou ignora a pergunta."""

    def interpret(self, text: str) -> ContextDecision:
        normalized = _normalize(text)

        negative = any(term in normalized for term in START_NEW)
        positive = any(term in normalized for term in CONTINUE)

        # "não, é outro assunto" tem os dois sinais — a negação manda.
        if negative:
            return ContextDecision.start_new
        if positive:
            return ContextDecision.continue_previous
        return ContextDecision.unclear

    @staticmethod
    def fallback_question(previous_channel_label: str, subject: str) -> str:
        """Usada quando não há modelo de linguagem para redigir a pergunta."""
        return (
            f"Vi que você estava tratando sobre {subject.lower()} pelo "
            f"{previous_channel_label}. Quer continuar nesse assunto por aqui, "
            f"ou prefere tratar de outra coisa?"
        )
