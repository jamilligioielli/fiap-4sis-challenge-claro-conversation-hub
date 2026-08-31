"""Comando de entrada de uma mensagem de cliente."""
from __future__ import annotations

from dataclasses import dataclass, field

from ...domain.value_objects.channel import Channel
from ...domain.value_objects.consent import Consent


@dataclass(frozen=True)
class IngestCommand:
    channel: Channel
    text: str
    customer_id: str | None = None
    external_id: str | None = None
    consent: Consent = field(default_factory=Consent)
