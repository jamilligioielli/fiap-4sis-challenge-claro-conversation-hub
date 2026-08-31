"""Detecção de que o cliente quer encerrar o atendimento.

Fica fora da taxonomia de intenções de propósito. "Obrigado" no meio de uma
negociação de plano é gentileza, não despedida — e classificar isso como
encerramento faria o assistente desligar na cara de quem estava sendo atendido.

O critério é a mensagem ser *predominantemente* uma despedida: curta e com um
termo de fechamento, ou um pedido explícito de encerrar.
"""
from __future__ import annotations

import re
import unicodedata

# Curta o bastante para que a despedida seja o assunto da mensagem, e não um
# adorno educado no fim de um pedido.
MAX_WORDS = 7

FAREWELL = (
    "tchau", "ate mais", "ate logo", "obrigado", "obrigada", "valeu",
    "era so isso", "so isso", "resolvido", "resolveu", "nada mais",
    "por enquanto e so", "e so isso", "muito obrigado", "muito obrigada",
)

EXPLICIT = (
    "pode encerrar", "encerrar atendimento", "finalizar atendimento",
    "pode finalizar", "encerra por aqui", "pode fechar o atendimento",
)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower().strip(" .!?,"))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class ClosureService:
    def wants_to_end(self, text: str) -> bool:
        normalized = _normalize(text)

        # Pedido explícito vale em qualquer tamanho de mensagem.
        if any(term in normalized for term in EXPLICIT):
            return True

        if len(normalized.split()) > MAX_WORDS:
            return False
        return any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in FAREWELL)
