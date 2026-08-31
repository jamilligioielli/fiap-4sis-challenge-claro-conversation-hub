"""Redator determinístico, por modelo de texto.

Não é um plano B de emergência: é a garantia de que o hub responde sem rede, sem
chave e sem cota. Também é o que mantém a demonstração possível em qualquer
condição de sala de aula.
"""
from __future__ import annotations

from ...domain.ports.response_generator import (GeneratedResponse, GenerationRequest,
                                                ResponseGenerator)
from ...domain.services.reply_composer import ReplyComposer
from ...domain.services.routing_service import Flow
from ...domain.value_objects.response_source import ResponseSource


class TemplateResponseGenerator(ResponseGenerator):
    def __init__(self, composer: ReplyComposer | None = None) -> None:
        self._composer = composer or ReplyComposer()

    @property
    def generator_name(self) -> str:
        return "modelo de texto"

    async def generate(self, request: GenerationRequest) -> GeneratedResponse:
        if request.fallback_text:
            return GeneratedResponse(text=request.fallback_text,
                                     source=ResponseSource.template)

        flow = self._flow_for(request)
        plan = request.customer.plan.name if request.customer and request.customer.plan else None

        text = self._composer.compose(
            flow, request.intent, request.business_facts, plan,
            text=request.customer_message,
        )
        return GeneratedResponse(text=text, source=ResponseSource.template)

    @staticmethod
    def _flow_for(request: GenerationRequest) -> Flow:
        raw = request.business_facts.get("__flow__")
        if isinstance(raw, Flow):
            return raw
        try:
            return Flow(str(raw))
        except ValueError:
            return Flow.fallback
