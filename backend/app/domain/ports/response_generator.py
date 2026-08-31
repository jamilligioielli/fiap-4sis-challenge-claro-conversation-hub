"""Porta de redação da resposta ao cliente.

Separada da classificação de propósito: entender o que o cliente quer e escrever
a resposta são problemas distintos, resolvidos por implementações distintas e
substituíveis em separado.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..entities.customer import Customer
from ..studio.studio_config import StudioConfig
from ..value_objects.channel import Channel
from ..value_objects.intent import Intent
from ..value_objects.response_source import ResponseSource


@dataclass
class GenerationRequest:
    """Tudo o que o redator precisa saber para escrever uma boa resposta."""

    channel: Channel
    intent: Intent
    config: StudioConfig
    customer: Customer | None = None
    business_facts: dict = field(default_factory=dict)
    """Dados vindos dos sistemas internos. O redator pode citá-los, jamais inventá-los."""
    transcript: list[dict] = field(default_factory=list)
    customer_message: str = ""
    directive: str = ""
    """Instrução do fluxo de negócio: o que esta resposta precisa realizar."""
    fallback_text: str = ""
    """Texto a usar quando não há redator generativo disponível.

    Saudação, pergunta de continuidade e abordagem ativa não são respostas de
    negócio — o redator determinístico não tem como derivá-las de um fluxo, e
    por isso quem chama informa o texto equivalente.
    """


@dataclass
class GeneratedResponse:
    text: str
    source: ResponseSource
    model: str | None = None


class ResponseGenerator(ABC):
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GeneratedResponse: ...

    @property
    @abstractmethod
    def generator_name(self) -> str: ...

    @property
    def uses_generative_ai(self) -> bool:
        """Se o texto é redigido na hora ou montado a partir de modelos prontos.

        Quem responde essa pergunta é o redator, não quem o instanciou: só ele
        sabe do que é capaz. A interface do simulador usa isso para dizer, em
        cada resposta, quem a escreveu — e o público merece essa distinção.
        """
        return False
