"""Classificador de intenção por modelo de linguagem."""
from __future__ import annotations

import json
import logging

from ...domain.ports.intent_classifier import IntentClassifier
from ...domain.studio.studio_config import StudioConfig
from ...domain.value_objects.area import Area
from ...domain.value_objects.intent import Intent
from ...domain.value_objects.intent_engine import IntentEngine
from .llm_client import LLMClient, LLMUnavailable
from .prompt_loader import PromptLoader
from .rule_based_classifier import TAXONOMY, extract_entities

log = logging.getLogger("hub.intent")

AREA_BY_SLUG = {slug: spec["area"] for slug, spec in TAXONOMY.items()}
LABEL_BY_SLUG = {slug: spec["label"] for slug, spec in TAXONOMY.items()}


class LLMIntentClassifier(IntentClassifier):
    def __init__(self, client: LLMClient, loader: PromptLoader,
                 studio: StudioConfig | None = None) -> None:
        self._client = client
        self._loader = loader
        self._studio = studio

    @property
    def engine_name(self) -> str:
        return f"IA ({self._client.model})"

    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent:
        prompt = self._loader.render(
            "intent_classification",
            intencoes=self._catalog(),
            historico=self._history(history),
            texto=text,
        )
        raw = await self._client.complete(prompt, max_tokens=300)
        return self._parse(raw, text)

    def _catalog(self) -> str:
        """Monta a lista a partir do Design Studio quando há configuração — assim,
        mapear uma intenção nova na interface muda o prompt sem implantação."""
        if self._studio and self._studio.intents:
            return "\n".join(
                f"- `{i.slug}`: {i.name}" + (f" (exemplos: {i.examples})" if i.examples else "")
                for i in self._studio.intents
            )
        return "\n".join(f"- `{slug}`: {label}" for slug, label in LABEL_BY_SLUG.items())

    @staticmethod
    def _history(history: list[str] | None) -> str:
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
        if slug not in LABEL_BY_SLUG:
            raise LLMUnavailable(f"slug fora da taxonomia: {slug!r}")

        confidence = float(data.get("confidence", 0.8))
        return Intent(
            slug=slug,
            name=LABEL_BY_SLUG[slug],
            confidence=max(0.0, min(confidence, 1.0)),
            area=AREA_BY_SLUG.get(slug, Area.suporte),
            entities={**extract_entities(original_text), **(data.get("entities") or {})},
            engine=IntentEngine.llm,
            reasoning=data.get("reasoning"),
        )
