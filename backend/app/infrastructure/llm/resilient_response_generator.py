"""Encadeia um redator primário e o seu reserva.

Aberto para extensão, fechado para modificação: acrescentar um terceiro redator
é encadear outro decorador, sem tocar em nenhum dos existentes.
"""
from __future__ import annotations

import logging

from ...domain.ports.response_generator import (GeneratedResponse, GenerationRequest,
                                                ResponseGenerator)

log = logging.getLogger("hub.generator")


class ResilientResponseGenerator(ResponseGenerator):
    def __init__(self, primary: ResponseGenerator, fallback: ResponseGenerator) -> None:
        self._primary = primary
        self._fallback = fallback
        self.last_generator = fallback.generator_name

    @property
    def generator_name(self) -> str:
        return f"{self._primary.generator_name} → {self._fallback.generator_name}"

    @property
    def uses_generative_ai(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GeneratedResponse:
        try:
            response = await self._primary.generate(request)
            self.last_generator = self._primary.generator_name
            return response
        except Exception as exc:  # noqa: BLE001
            log.warning("Redator generativo indisponível (%s) — usando modelo de texto", exc)
            self.last_generator = self._fallback.generator_name
            return await self._fallback.generate(request)
