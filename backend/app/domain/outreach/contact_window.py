"""Janela de atendimento livre.

Depois da última mensagem do cliente, a empresa tem 24 horas para responder
livremente. Passado esse prazo, o contato só pode ser retomado por um modelo
aprovado. A regra existe para impedir que a marca fale quando bem entender.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class ContactWindow:
    last_inbound_at: datetime | None

    @property
    def is_open(self) -> bool:
        if self.last_inbound_at is None:
            return False
        return self._elapsed() < WINDOW

    @property
    def hours_remaining(self) -> float:
        if not self.is_open:
            return 0.0
        return round((WINDOW - self._elapsed()).total_seconds() / 3600, 1)

    def _elapsed(self) -> timedelta:
        moment = self.last_inbound_at
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - moment
