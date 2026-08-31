"""Pesquisa de satisfação disparada ao fim do atendimento.

Fica no agregado da conversa, e não numa tabela à parte, porque a nota só
significa alguma coisa junto do atendimento que a produziu: qual foi o assunto,
quantas mensagens levou, se passou por um humano. Nota solta é número; nota
presa à conversa é diagnóstico.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..value_objects.clock import utcnow

# Faixas clássicas do NPS. Ficam aqui, e não espalhadas nas telas, porque a
# fronteira entre detrator e neutro é regra de negócio, não formatação.
DETRACTOR_MAX = 6
PASSIVE_MAX = 8


class NpsSurvey(BaseModel):
    """Uma pesquisa enviada, e a resposta quando ela vem.

    `sent_at` sem `answered_at` é o caso mais comum na vida real: a maioria das
    pesquisas não é respondida, e o sistema precisa saber a diferença entre
    "não perguntamos" e "perguntamos e ninguém respondeu".
    """

    sent_at: datetime = Field(default_factory=utcnow)
    answered_at: datetime | None = None
    score: int | None = None
    comment: str = ""
    closed_by: str = Field(
        default="bot",
        description="Quem encerrou o atendimento: 'bot' ou o nome do atendente.",
    )
    attempts: int = Field(
        default=0,
        description="Quantas vezes o cliente respondeu algo que não era uma nota. "
                    "Insistir indefinidamente transforma a pesquisa em incômodo.",
    )
    dismissed: bool = Field(
        default=False,
        description="A pesquisa foi encerrada sem nota — o cliente recusou ou não "
                    "respondeu depois de uma insistência. É diferente de 'ainda "
                    "esperando': aqui o hub já parou de perguntar.",
    )

    def record(self, score: int, comment: str = "") -> None:
        if not 0 <= score <= 10:
            raise ValueError("A nota de NPS vai de 0 a 10.")
        self.score = score
        self.comment = comment
        self.answered_at = utcnow()

    @property
    def answered(self) -> bool:
        return self.score is not None

    @property
    def open(self) -> bool:
        """Enviada, sem nota e ainda perguntando."""
        return not self.answered and not self.dismissed

    @property
    def category(self) -> str:
        if self.score is None:
            return "sem resposta"
        if self.score <= DETRACTOR_MAX:
            return "detrator"
        if self.score <= PASSIVE_MAX:
            return "neutro"
        return "promotor"
