"""Adaptador do RF002 sobre o protocolo OpenAI (`POST /chat/completions`).

Escolhemos falar o *protocolo*, e nao um provedor. Isso torna intercambiaveis,
sem uma linha de codigo alterada:

  Groq                https://api.groq.com/openai/v1            (tier gratuito, sem cartão)
  Google AI Studio    https://generativelanguage.googleapis.com/v1beta/openai
  OpenAI              https://api.openai.com/v1                 (pago)
  OpenRouter          https://openrouter.ai/api/v1
  Ollama local        http://localhost:11434/v1

Trocar de provedor = trocar LLM_BASE_URL + LLM_MODEL + LLM_API_KEY no .env.
E exatamente o que o principio da inversao de dependencia compra na pratica.
"""
from __future__ import annotations

import json
import logging

import httpx

from ...domain.ports import IntentClassifier
from ...domain.studio import StudioConfig
from ...domain.value_objects import Area, Intent, IntentEngine
from ...settings import LLMSettings
from .prompt_loader import PromptLoader
from .rule_based_classifier import TAXONOMY, extract_entities

log = logging.getLogger("hub.llm")

_AREA_BY_SLUG = {slug: spec["area"] for slug, spec in TAXONOMY.items()}
_LABEL_BY_SLUG = {slug: spec["label"] for slug, spec in TAXONOMY.items()}


class LLMUnavailable(RuntimeError):
    """Levantada quando o provedor nao responde ou responde fora do contrato."""


class OpenAICompatibleClassifier(IntentClassifier):
    def __init__(self, settings: LLMSettings, loader: PromptLoader,
                 studio: StudioConfig | None = None) -> None:
        self._s = settings
        self._loader = loader
        self._studio = studio

    @property
    def engine_name(self) -> str:
        return f"llm ({self._s.model})"

    # ------------------------------------------------------------------ API
    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent:
        prompt = self._loader.render(
            "intent_classification",
            intencoes=self._intent_catalog(),
            historico=self._format_history(history),
            texto=text,
        )
        raw = await self.complete(prompt, max_tokens=300)
        return self._parse(raw, text)

    async def complete(self, prompt: str, *, system: str | None = None,
                       max_tokens: int | None = None) -> str:
        """Chamada bruta ao provedor. Reusada pelos casos de uso que geram
        resumo e sugestoes, nao so pela classificacao."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._s.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens or self._s.max_tokens,
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

    # -------------------------------------------------------------- helpers
    def _intent_catalog(self) -> str:
        """Monta a lista de intencoes a partir do Design Studio quando ha
        configuracao carregada -- assim, mapear uma intencao nova na interface
        muda o prompt sem deploy."""
        if self._studio and self._studio.intents:
            return "\n".join(
                f"- `{i.slug}`: {i.name}" + (f" (exemplos: {i.examples})" if i.examples else "")
                for i in self._studio.intents
            )
        return "\n".join(f"- `{slug}`: {label}" for slug, label in _LABEL_BY_SLUG.items())

    @staticmethod
    def _format_history(history: list[str] | None) -> str:
        if not history:
            return "(primeira mensagem desta conversa)"
        return "\n".join(f"- {line}" for line in history[-6:])

    @staticmethod
    def _parse(raw: str, original_text: str) -> Intent:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise LLMUnavailable("resposta do modelo sem JSON reconhecível")

        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"JSON inválido: {exc}") from exc

        slug = data.get("slug", "nao_identificada")
        if slug not in _LABEL_BY_SLUG:
            raise LLMUnavailable(f"slug fora da taxonomia: {slug!r}")

        confidence = float(data.get("confidence", 0.8))
        return Intent(
            slug=slug,
            name=_LABEL_BY_SLUG[slug],
            confidence=max(0.0, min(confidence, 1.0)),
            area=_AREA_BY_SLUG.get(slug, Area.suporte),
            entities={**extract_entities(original_text), **(data.get("entities") or {})},
            engine=IntentEngine.llm,
            reasoning=data.get("reasoning"),
        )


class ResilientIntentClassifier(IntentClassifier):
    """Decorator: tenta o classificador primario e cai para o secundario.

    Aberto para extensao, fechado para modificacao -- acrescentar um terceiro
    provedor e encadear outro decorator, sem tocar em nenhum dos existentes.
    """

    def __init__(self, primary: IntentClassifier, fallback: IntentClassifier) -> None:
        self._primary = primary
        self._fallback = fallback
        self.last_engine = fallback.engine_name

    @property
    def engine_name(self) -> str:
        return f"{self._primary.engine_name} → {self._fallback.engine_name}"

    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent:
        try:
            intent = await self._primary.classify(text, history=history)
            self.last_engine = self._primary.engine_name
            return intent
        except Exception as exc:  # noqa: BLE001
            log.warning("Classificador primário indisponível (%s) — usando regras", exc)
            self.last_engine = self._fallback.engine_name
            return await self._fallback.classify(text, history=history)
