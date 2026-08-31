"""Cliente da Claro."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..value_objects.channel import Channel
from .plan import Plan
from .timeline_event import TimelineEvent


class Customer(BaseModel):
    id: str
    name: str
    document_masked: str = ""
    birth_date: str = ""
    customer_since: str = ""
    segment: str = "Padrão"
    email: str = ""
    phone: str = ""
    preferred_channel: Channel = Channel.whatsapp
    plan: Plan | None = None
    products: list[dict] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    churn_risk: float = 0.0
    churn_factors: list[dict] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)

    persona_summary: str = Field(
        default="",
        description="Como esta pessoa costuma se comportar. Entra no contexto do "
                    "assistente para que a resposta considere quem está do outro lado.",
    )
    marketing_opt_in: bool = Field(
        default=False,
        description="Autorização explícita para contato ativo com oferta. "
                    "Sem ela, a Claro não inicia conversa comercial.",
    )
    last_inbound_at: datetime | None = Field(
        default=None,
        description="Última mensagem enviada pelo cliente. Define a janela de "
                    "atendimento livre no WhatsApp.",
    )

    @property
    def first_name(self) -> str:
        return self.name.split(" ")[0] if self.name else ""

    @property
    def churn_label(self) -> str:
        if self.churn_risk < 0.25:
            return "Baixo"
        return "Médio" if self.churn_risk < 0.6 else "Alto"
