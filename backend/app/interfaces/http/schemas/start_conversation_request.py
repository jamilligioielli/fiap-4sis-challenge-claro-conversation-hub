"""Abertura de uma conversa pelo simulador."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ....domain.value_objects.channel import Channel


class StartConversationRequest(BaseModel):
    """Abrir a conversa antes da primeira mensagem permite que o assistente
    cumprimente por iniciativa própria, em vez de esperar o cliente falar
    sozinho com uma tela vazia."""

    customer_id: str
    channel: Channel = Channel.whatsapp
