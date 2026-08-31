"""Porta de saída para um canal externo."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..value_objects.channel import Channel


class OutboundGateway(ABC):
    """O hub responde de duas formas conforme o canal: síncrona, quando o canal
    lê a resposta na mesma requisição; e assíncrona, quando a resposta precisa
    ser empurrada de volta por outra chamada. Esta porta cobre o segundo caso."""

    channel: Channel
    enabled: bool

    @abstractmethod
    async def send(self, to: str, text: str) -> dict: ...
