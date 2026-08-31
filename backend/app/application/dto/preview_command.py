"""Comando de pré-visualização do efeito da persona."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewPersonaCommand:
    """Reescreve uma mensagem de exemplo com a configuração vigente, para que a
    equipe veja o efeito do ajuste antes de valer para os clientes."""

    message: str
    channels: tuple[str, ...] = ("whatsapp", "webchat", "app")
    customer_id: str | None = None
