"""Leitura da resposta do cliente à pesquisa de satisfação.

O cliente não responde `{"score": 9}`. Ele escreve "9", "nota 9", "daria uns 8",
"10!!" ou "não quero responder". Interpretar isso é regra de negócio — e é o que
separa uma pesquisa que funciona no WhatsApp de um formulário disfarçado de
conversa.
"""
from __future__ import annotations

import re
import unicodedata

MIN_SCORE, MAX_SCORE = 0, 10

# Aceita "9", "nota 9", "eu dou 9", "9/10", "9 de 10". A âncora de palavra evita
# capturar o 30 de "meu plano de 30GB" numa mensagem que não é resposta.
SCORE = re.compile(r"(?<![\d,.])(10|[0-9])(?![\d,.])")

WRITTEN = {
    "zero": 0, "um": 1, "dois": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}

DECLINED = (
    "nao quero", "nao vou responder", "prefiro nao", "deixa pra la", "sem nota",
    "nao responder", "pula", "depois eu respondo", "nao tenho interesse",
)


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class NpsService:
    """Interpreta a nota e redige as falas da pesquisa."""

    def interpret(self, text: str) -> int | None:
        """Devolve a nota, ou `None` quando não há nota reconhecível."""
        normalized = _normalize(text)

        if any(term in normalized for term in DECLINED):
            return None

        for word, value in WRITTEN.items():
            if re.search(rf"\b{word}\b", normalized):
                return value

        if (match := SCORE.search(normalized)):
            score = int(match.group(1))
            if MIN_SCORE <= score <= MAX_SCORE:
                return score
        return None

    def declined(self, text: str) -> bool:
        """O cliente disse, com todas as letras, que não quer responder."""
        return any(term in _normalize(text) for term in DECLINED)

    @staticmethod
    def question(first_name: str = "") -> str:
        nome = f", {first_name}" if first_name else ""
        return (f"Antes de encerrar{nome}: de 0 a 10, o quanto você recomendaria a Claro "
                f"para um amigo ou familiar? Pode responder só com o número.")

    @staticmethod
    def acknowledgement(score: int, first_name: str = "") -> str:
        """A resposta muda com a nota — agradecer igual a quem deu 2 e a quem deu
        10 é a forma mais rápida de provar que ninguém leu."""
        nome = first_name or "você"
        if score <= 6:
            return (f"Obrigada pela sinceridade, {nome}. Uma nota assim diz que a gente "
                    f"ficou devendo, e isso vai para a equipe responsável. "
                    f"Atendimento encerrado — estamos por aqui quando precisar.")
        if score <= 8:
            return (f"Obrigada pela nota, {nome}! Anotado o que ainda dá para melhorar. "
                    f"Atendimento encerrado — é só chamar quando precisar.")
        return (f"Que bom, {nome}, obrigada! Fico feliz que tenha ajudado. "
                f"Atendimento encerrado — estamos por aqui quando precisar.")

    @staticmethod
    def retry() -> str:
        return ("Só preciso de um número de 0 a 10 — mas se preferir não responder, "
                "é só dizer e eu encerro por aqui.")

    @staticmethod
    def farewell() -> str:
        return ("Sem problema! Atendimento encerrado — estamos por aqui quando precisar.")
