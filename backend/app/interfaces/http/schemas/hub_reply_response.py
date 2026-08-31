"""Resposta do hub a uma mensagem de canal."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ....domain.value_objects.channel import Channel
from .intent_response import IntentResponse


class HubReplyResponse(BaseModel):
    conversation_id: str
    session_id: str
    customer_id: str
    channel: Channel
    reply: str = Field(description="Texto a devolver ao cliente, já na voz da marca.")
    intent: IntentResponse
    flow: str = Field(description="Fluxo de negócio acionado.")
    persona_applied: str = Field(description="Configuração de persona usada nesta resposta.")
    persona_version: int = Field(
        description="Versão da configuração vigente. Muda a cada ajuste no Design Studio, "
                    "o que permite provar que a alteração chegou à conversa.")
    response_source: str = Field(
        description="`generative` quando o texto foi redigido por modelo de linguagem, "
                    "`template` quando veio do redator determinístico.")
    response_model: str | None = Field(
        default=None, description="Modelo que redigiu, quando generativo.")
    context_recovered: bool = Field(
        description="Verdadeiro quando o hub retomou uma conversa já existente.")
    context_note: str | None = Field(
        default=None, description="Preenchido quando houve troca de canal.")
    awaiting_context_confirmation: bool = Field(
        default=False,
        description="O hub perguntou se o cliente quer retomar o assunto anterior e "
                    "aguarda a resposta antes de prosseguir.")
    handover_triggered: bool = False
    handover_reason: str | None = None
    services_consulted: list[str] = Field(default_factory=list)
    turns: int = 0
    awaiting_nps: bool = Field(
        default=False,
        description="A pesquisa de satisfação foi enviada e o hub aguarda a nota. "
                    "Enquanto verdadeiro, a próxima mensagem do cliente é lida como "
                    "resposta à pesquisa, e não como novo pedido.")
    conversation_closed: bool = Field(
        default=False, description="O atendimento foi encerrado nesta conversa.")
    nps_score: int | None = Field(
        default=None, description="Nota de 0 a 10, quando o cliente já respondeu.")
    superseded: bool = Field(
        default=False,
        description="Esta mensagem foi agrupada com outra mais recente do mesmo cliente "
                    "e não gerou resposta própria — o hub aguarda o cliente terminar de "
                    "escrever antes de responder. A resposta sai na última chamada do lote.")
