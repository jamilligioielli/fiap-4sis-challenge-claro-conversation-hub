"""Mensagem enviada pelo atendente."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ....domain.value_objects.channel import Channel


class AgentMessageRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"text": "Oi Maria, sou a Ana. Já vi todo o histórico, pode deixar comigo."}]})

    text: str = Field(min_length=1, max_length=4000)
    channel: Channel | None = Field(
        default=None, description="Se omitido, responde pelo último canal do cliente.")
