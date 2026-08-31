"""Resultado do encerramento."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .conversation_list_item import ConversationListItem


class CloseConversationResponse(BaseModel):
    conversation: ConversationListItem
    survey_sent: bool = Field(description="A pesquisa foi enviada ao cliente.")
    survey_message: str = Field(
        default="", description="Texto exato da pergunta entregue ao cliente.")
