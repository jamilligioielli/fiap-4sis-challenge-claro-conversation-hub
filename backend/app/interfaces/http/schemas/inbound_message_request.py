"""Mensagem que um canal entrega ao hub."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ....domain.value_objects.consent import Consent


class InboundMessageRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "text": "Olá, gostaria de alterar meu plano",
        "customer_id": "cust_maria_silva",
        "consent": {"granted": True, "scope": ["atendimento"]},
    }]})

    text: str = Field(min_length=1, max_length=4000,
                      description="Conteúdo da mensagem, como o cliente escreveu.")
    external_id: str | None = Field(
        default=None,
        description=("Identificador do cliente neste canal: telefone, cookie de sessão, "
                     "device id. O hub resolve para o identificador interno do cliente."),
    )
    customer_id: str | None = Field(
        default=None,
        description="Informe quando o canal já autenticou o cliente.",
    )
    consent: Consent = Field(
        default_factory=Consent,
        description="Consentimento do cliente para este canal. Sem ele o hub recusa.",
    )
