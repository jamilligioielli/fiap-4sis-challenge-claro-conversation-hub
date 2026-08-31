"""Encerramento do atendimento pelo console."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CloseConversationRequest(BaseModel):
    agent: str = Field(
        default="Console",
        description="Quem encerrou. Fica registrado na pesquisa, porque um 6 depois "
                    "de um atendente conta história diferente de um 6 resolvido pelo bot.",
        examples=["Ana Ribeiro"],
    )
    survey: bool = Field(
        default=True,
        description="Dispara a pesquisa de satisfação junto do encerramento.",
    )
