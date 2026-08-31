"""Cliente elegível a contato ativo."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EligibleCustomerResponse(BaseModel):
    customer_id: str
    customer_name: str
    segment: str = ""
    score: float = Field(description="Soma dos pesos das razões de elegibilidade.")
    reasons: list[dict] = Field(
        description="Por que este cliente foi selecionado. Abordar alguém sem "
                    "saber o motivo é como se perde a confiança do cliente.")
    blocks: list[dict] = Field(
        description="Impedimentos ao contato. Bloqueio não é erro: é a política funcionando.")
    suggested_offer: dict | None = None
    window_open: bool = Field(
        description="Se a janela de atendimento livre está aberta. Fora dela, o contato "
                    "só pode sair por modelo de mensagem previamente aprovado.")
    window_hours_remaining: float = 0.0
    marketing_opt_in: bool = False
    can_contact: bool = False
    requires_template: bool = False
