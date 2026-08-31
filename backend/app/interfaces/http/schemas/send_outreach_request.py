"""Disparo de contato ativo pelo console."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SendOutreachRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"customer_id": "cust_maria_silva", "offer_id": "upgrade_flex_50",
         "agent": "Paula · Operação"}]})

    customer_id: str
    offer_id: str
    channel: str = "whatsapp"
    agent: str = "Console"
    custom_message: str | None = Field(
        default=None, description="Substitui o texto sugerido da oferta.")
