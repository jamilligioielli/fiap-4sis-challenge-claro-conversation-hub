"""Redator de respostas por modelo de linguagem.

Este é o adaptador que torna a conversa *generativa*: o texto que o cliente lê é
escrito na hora, considerando a persona configurada, os guardrails, o tom do
canal, quem é o cliente, o que os sistemas internos apuraram e tudo o que já foi
dito na conversa.

A separação em relação ao classificador é deliberada. Entender o que o cliente
quer e escrever a resposta são problemas diferentes: o primeiro precisa ser
previsível e barato, o segundo precisa soar humano. Misturá-los num único prompt
piora os dois.
"""
from __future__ import annotations

import logging

from ...domain.ports.response_generator import (GeneratedResponse, GenerationRequest,
                                                ResponseGenerator)
from ...domain.value_objects.response_source import ResponseSource
from .llm_client import LLMClient, LLMUnavailable
from .prompt_loader import PromptLoader
from .text_cleanup import clean_reply

log = logging.getLogger("hub.generator")

MAX_TRANSCRIPT_TURNS = 10


class LLMResponseGenerator(ResponseGenerator):
    def __init__(self, client: LLMClient, loader: PromptLoader,
                 prompt_name: str = "response_generation") -> None:
        self._client = client
        self._loader = loader
        self._prompt_name = prompt_name

    @property
    def generator_name(self) -> str:
        return f"IA generativa ({self._client.model})"

    @property
    def uses_generative_ai(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GeneratedResponse:
        prompt = self._loader.render(self._prompt_name, **self._variables(request))

        text = await self._client.complete(prompt, max_tokens=380, temperature=0.6)
        text = clean_reply(text)

        if not text:
            raise LLMUnavailable("O modelo devolveu uma resposta vazia.")

        return GeneratedResponse(
            text=text,
            source=ResponseSource.generative,
            model=self._client.model,
        )

    # ------------------------------------------------------------- variáveis
    def _variables(self, request: GenerationRequest) -> dict:
        config = request.config
        channel = config.channel(request.channel.studio_id)

        return {
            "persona_nome": config.persona.name,
            "persona_descricao": config.persona.description,
            "tracos": ", ".join(config.persona.traits) or "—",
            "guardrails": self._guardrails(config),
            "canal": channel.name if channel else request.channel.label,
            "formalidade": channel.formality_label if channel else "Equilibrado",
            "emojis": "permitidos, com moderação" if channel and channel.useEmoji
                      else "não usar",
            "tamanho_max": channel.maxLength if channel else 280,
            "cliente": self._customer(request),
            "fatos": self._facts(request),
            "historico": self._transcript(request),
            "mensagem": request.customer_message or "(o cliente ainda não escreveu nada)",
            "objetivo": request.directive or "Ajudar o cliente com o que ele pediu.",
            "contexto": request.directive or "Primeiro contato desta conversa.",
            "assunto_anterior": request.intent.name,
            "canal_anterior": request.business_facts.get("canal_anterior", "outro canal"),
            "canal_atual": request.channel.label,
            "motivos": request.business_facts.get("motivos", "—"),
            "oferta": request.business_facts.get("oferta", "—"),
        }

    @staticmethod
    def _guardrails(config) -> str:
        if not config.guardrails:
            return "- Nunca inventar informação sobre a conta do cliente."
        return "\n".join(f"- {g.rule}  ({g.category})" for g in config.guardrails)

    @staticmethod
    def _customer(request: GenerationRequest) -> str:
        customer = request.customer
        if customer is None:
            return ("Cliente ainda não identificado. Trate com cordialidade e sem "
                    "presumir nada sobre a conta dele.")

        lines = [f"Nome: {customer.name} (chame de {customer.first_name})"]
        if customer.segment:
            lines.append(f"Segmento: {customer.segment}")
        if customer.customer_since:
            lines.append(f"Cliente desde: {customer.customer_since}")
        if customer.plan:
            plan = customer.plan
            lines.append(
                f"Plano atual: {plan.name} por R$ {plan.price:.2f}/mês, "
                f"usando {plan.usage_percent}% da franquia de {plan.data_gb}GB"
            )
        if customer.persona_summary:
            lines.append(f"Perfil: {customer.persona_summary}")
        return "\n".join(f"- {line}" for line in lines)

    @staticmethod
    def _facts(request: GenerationRequest) -> str:
        facts = {k: v for k, v in request.business_facts.items()
                 if k not in ("canal_anterior", "motivos", "oferta")}
        if not facts:
            return "(nenhuma consulta a sistema interno foi necessária nesta mensagem)"

        lines: list[str] = []
        for service, payload in facts.items():
            lines.append(f"### {service}")
            lines.append(_describe(payload))
        return "\n".join(lines)

    @staticmethod
    def _transcript(request: GenerationRequest) -> str:
        turns = request.transcript[-MAX_TRANSCRIPT_TURNS:]
        if not turns:
            return "(esta é a primeira mensagem da conversa)"

        speaker = {"customer": "Cliente", "bot": "Você", "agent": "Atendente humano",
                   "system": "Sistema"}
        return "\n".join(
            f"{speaker.get(t.get('author'), t.get('author'))}: {t.get('text', '')}"
            for t in turns
        )


def _describe(value, indent: int = 0) -> str:
    """Serializa os dados dos sistemas internos de forma legível para o modelo.

    JSON cru funciona, mas gasta tokens com chaves e aspas e faz o modelo copiar
    nomes técnicos para dentro da resposta ao cliente.
    """
    pad = "  " * indent
    if isinstance(value, dict):
        return "\n".join(
            f"{pad}- {key}: {_inline(inner)}" if not isinstance(inner, (dict, list))
            else f"{pad}- {key}:\n{_describe(inner, indent + 1)}"
            for key, inner in value.items()
        )
    if isinstance(value, list):
        return "\n".join(
            f"{pad}- {_inline(item)}" if not isinstance(item, (dict, list))
            else _describe(item, indent + 1)
            for item in value
        )
    return f"{pad}- {value}"


def _inline(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}".replace(".", ",")
    return str(value)
