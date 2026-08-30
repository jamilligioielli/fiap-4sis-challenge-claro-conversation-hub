"""Servico de dominio: aplicacao da persona (RF006).

O tom de voz da Claro e um servico do hub, nao um prompt copiado dentro de cada
integracao. Mudar a configuracao no Design Studio muda, ja na proxima resposta,
o jeito da Claro falar em todos os canais integrados.

Funcao pura: recebe texto + configuracao, devolve texto. Sem I/O, sem estado.
"""
from __future__ import annotations

import re

from ..studio import ChannelConfig, StudioConfig
from ..value_objects import Channel

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️]+"
)

_CASUAL = (
    ("Ficarei feliz em auxiliar", "Posso te ajudar"),
    ("Gostaria de informar que", "Olha só:"),
    ("Informamos que", "Olha,"),
    ("Prezado(a)", "Oi"),
    ("Solicito que", "Preciso que"),
)


class PersonaService:
    def apply(self, text: str, config: StudioConfig, channel: Channel, *,
              customer_first_name: str = "", greet: bool = False) -> str:
        ch = config.channel(channel.studio_id)
        if ch is None:
            return text.strip()

        if greet and ch.greeting:
            greeting = self._interpolate(ch.greeting, customer_first_name)
            if greeting:
                text = f"{greeting} {text}"

        text = self._adjust_formality(text, ch.formalityLevel)

        if not ch.useEmoji:
            text = EMOJI.sub("", text)

        text = re.sub(r"\s{2,}", " ", text).strip()
        return self._truncate(text, ch.maxLength)

    @staticmethod
    def _interpolate(template: str, first_name: str) -> str:
        """Interpola o nome e limpa a pontuação órfã.

        Cliente anônimo é o caso comum no primeiro contato de um canal aberto:
        "Olá, {nome}!" sem nome não pode virar "Olá, !".
        """
        text = template.replace("{nome}", first_name)
        if not first_name:
            text = re.sub(r"[,\s]+([!?.])", r"\1", text)
            text = re.sub(r"[,\s]+$", "", text)
        return re.sub(r"\s{2,}", " ", text).strip()

    @staticmethod
    def _adjust_formality(text: str, level: int) -> str:
        if level < 40:
            for formal, casual in _CASUAL:
                text = text.replace(formal, casual)
        elif level > 65:
            for formal, casual in _CASUAL:
                text = text.replace(casual, formal)
        return text

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        """A URA corta em fronteira de frase: audio cortado no meio de uma
        palavra e pior do que audio curto."""
        if limit <= 0 or len(text) <= limit:
            return text
        cut = text[:limit]
        for sep in (". ", "? ", "! "):
            if (idx := cut.rfind(sep)) > limit * 0.5:
                return cut[: idx + 1].strip()
        return cut.rsplit(" ", 1)[0].rstrip(".,;:") + "…"

    @staticmethod
    def describe(config: StudioConfig, channel: Channel) -> str:
        ch = config.channel(channel.studio_id)
        if ch is None:
            return config.persona.name
        return (f"{config.persona.name} · {ch.name} · {ch.formality_label}"
                f" · emojis {'ON' if ch.useEmoji else 'OFF'}")

    @staticmethod
    def guardrail_summary(config: StudioConfig) -> list[str]:
        return [g.rule for g in config.guardrails]
