"""Envio direto pelo número do MVP, para validar credenciais."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppSendRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"to": "5511987654321", "text": "Teste de integração do Claro Conversation Hub."}]})

    text: str = Field(min_length=1, max_length=4000)
    to: str | None = Field(default=None, description="Telefone internacional, só dígitos.")
