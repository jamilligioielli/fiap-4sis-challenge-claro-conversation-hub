"""Diagnóstico da integração com o WhatsApp Business.

Consumido apenas pela documentação e pela operação — nunca carrega segredo.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class WhatsAppStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    can_send: bool
    api_version: str
    phone_number_id: str = Field(description="Mascarado.")
    business_account_id: str = Field(description="Mascarado.")
    access_token: str = Field(description="`configurado` ou `ausente`.")
    verify_token: str = Field(description="`configurado` ou `ausente`.")
    signature_validation: bool
    default_recipient: str = Field(description="Mascarado.")
    webhook_url: str
    missing: list[str]
