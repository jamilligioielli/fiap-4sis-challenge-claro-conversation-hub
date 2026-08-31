"""Elegibilidade de um cliente para contato ativo."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .offer import Offer


class EligibilityReason(BaseModel):
    """Por que este cliente foi selecionado. A razão é exibida ao gestor antes
    do disparo — abordar alguém sem saber o motivo é como a operadora perde
    a confiança que levou anos para construir."""

    code: str
    description: str
    weight: float = Field(ge=0.0, le=1.0)


class OutreachBlock(BaseModel):
    """Impedimento ao contato. Bloqueio não é erro: é a política funcionando."""

    code: str
    description: str


class EligibleCustomer(BaseModel):
    customer_id: str
    customer_name: str
    segment: str = ""
    reasons: list[EligibilityReason] = Field(default_factory=list)
    blocks: list[OutreachBlock] = Field(default_factory=list)
    suggested_offer: Offer | None = None
    window_open: bool = False
    window_hours_remaining: float = 0.0
    marketing_opt_in: bool = False

    @property
    def score(self) -> float:
        return round(sum(r.weight for r in self.reasons), 2)

    @property
    def can_contact(self) -> bool:
        return not self.blocks and self.suggested_offer is not None

    @property
    def requires_template(self) -> bool:
        """Fora da janela, o contato só sai por modelo aprovado."""
        return not self.window_open
