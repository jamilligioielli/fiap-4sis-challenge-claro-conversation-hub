"""Pedido de transferência para atendente."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HandoverRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"reason": "Cliente solicitou atendimento humano", "agent": "Ana · CX"}]})

    reason: str = Field(default="Solicitado pelo console")
    agent: str | None = Field(default=None, description="Atendente que assume a conversa.")
