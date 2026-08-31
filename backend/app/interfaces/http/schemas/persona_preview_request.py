"""Pré-visualização do efeito da persona."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PersonaPreviewRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"message": "Posso te ajudar com a alteração do seu plano. Qual você prefere?"}]})

    message: str = Field(min_length=1, max_length=1000,
                         description="Texto de negócio a ser vestido com a persona.")
    channels: list[str] = Field(default_factory=lambda: ["whatsapp", "webchat", "app"])
    customer_id: str | None = None
