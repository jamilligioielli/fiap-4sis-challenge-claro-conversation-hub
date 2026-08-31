"""Cliente HTTP do protocolo OpenAI (`POST /chat/completions`).

Escolhemos falar o *protocolo*, e não um provedor. Isso torna intercambiáveis,
sem uma linha de código alterada:

    Groq              https://api.groq.com/openai/v1            (gratuito, sem cartão)
    Google AI Studio  https://generativelanguage.googleapis.com/v1beta/openai
    OpenAI            https://api.openai.com/v1
    OpenRouter        https://openrouter.ai/api/v1
    Ollama local      http://localhost:11434/v1

Trocar de provedor é trocar três variáveis de ambiente.

Cada provedor acrescenta campos próprios ao protocolo, e o cliente não os
conhece por nome: eles chegam prontos em `LLM_EXTRA_PARAMS`. Assim, ligar o
`include_reasoning` da Groq ou o `reasoning_effort` de um modelo de raciocínio
é editar o `.env`, e não este arquivo.
"""
from __future__ import annotations

import logging

import httpx

from ...settings import LLMSettings

log = logging.getLogger("hub.llm")


class LLMUnavailable(RuntimeError):
    """O provedor não respondeu, ou respondeu fora do contrato esperado."""


class LLMClient:
    def __init__(self, settings: LLMSettings) -> None:
        self._s = settings

    @property
    def model(self) -> str:
        return self._s.model

    @property
    def enabled(self) -> bool:
        return self._s.enabled

    async def complete(self, prompt: str, *, system: str | None = None,
                       max_tokens: int | None = None,
                       temperature: float = 0.0) -> str:
        if not self._s.enabled:
            raise LLMUnavailable("Nenhuma chave de modelo de linguagem configurada.")

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._s.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self._s.max_tokens,
            # Campos próprios do provedor, vindos da configuração. Um modelo de
            # raciocínio como o gpt-oss devolve o raciocínio junto da resposta
            # se ninguém pedir o contrário, e esse texto não pode chegar ao
            # cliente. Desligar isso é obrigação do adaptador, não do redator.
            **self._s.extra_params,
        }

        try:
            async with httpx.AsyncClient(timeout=self._s.timeout) as client:
                response = await client.post(
                    f"{self._s.base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._s.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMUnavailable(str(exc)) from exc
