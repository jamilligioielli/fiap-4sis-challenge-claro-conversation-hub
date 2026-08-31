"""Resultado de um disparo de contato ativo."""
from __future__ import annotations

from pydantic import BaseModel, Field


class OutreachResultResponse(BaseModel):
    conversation_id: str
    customer_id: str
    message: str = Field(description="O que foi enviado ao cliente.")
    channel: str
    template_category: str
    used_template: bool = Field(
        description="Verdadeiro quando a janela estava fechada e foi preciso usar "
                    "um modelo aprovado em vez de texto livre.")
    response_source: str
