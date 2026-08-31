"""Consentimento do cliente, por canal e por finalidade."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .clock import utcnow


class Consent(BaseModel):
    """Viaja dentro do próprio evento, e não numa tabela à parte, para que
    nenhuma etapa do processamento consiga tratar o dado sem saber o que foi
    autorizado."""

    model_config = ConfigDict(frozen=True)

    granted: bool = True
    scope: tuple[str, ...] = ("atendimento",)
    captured_at: datetime = Field(default_factory=utcnow)

    def allows(self, purpose: str) -> bool:
        return self.granted and purpose in self.scope
