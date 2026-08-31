"""Como a mesma mensagem sai em cada canal."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChannelPreview(BaseModel):
    channel_id: str
    channel_name: str
    formality_label: str
    use_emoji: bool
    max_length: int
    rendered: str = Field(description="A mensagem já com a persona aplicada.")
    length: int


class PersonaPreviewResponse(BaseModel):
    """Existe para tornar visível o que normalmente só se percebe conversando:
    mudar o tom no Design Studio muda a fala em todos os canais."""

    persona_name: str
    persona_version: int
    original: str
    previews: list[ChannelPreview]
