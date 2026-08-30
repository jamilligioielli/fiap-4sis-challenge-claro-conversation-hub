"""Adaptador do RF002: classificador deterministico por palavra-chave.

Nao e um "plano B de emergencia" -- e a garantia de que a demonstracao funciona
sem rede, sem chave e sem cota. O hub sempre tem este classificador disponivel.
"""
from __future__ import annotations

import re
import unicodedata

from ...domain.ports import IntentClassifier
from ...domain.value_objects import Area, Intent, IntentEngine, UNIDENTIFIED

TAXONOMY: dict[str, dict] = {
    "alteracao_plano": {
        "label": "Alteração de Plano", "area": Area.vendas,
        "keywords": ["alterar meu plano", "mudar de plano", "trocar de plano", "alterar plano",
                     "mudar plano", "upgrade", "aumentar o plano", "migrar plano",
                     "quero o claro flex", "contratar plano", "mudar meu plano"],
    },
    "segunda_via_fatura": {
        "label": "Segunda Via de Fatura", "area": Area.financeiro,
        "keywords": ["segunda via", "2 via", "minha fatura", "boleto", "conta atrasada",
                     "codigo de barras", "vencimento", "pagar a conta", "fatura"],
    },
    "suporte_tecnico": {
        "label": "Suporte Técnico", "area": Area.suporte,
        "keywords": ["internet lenta", "sem sinal", "nao conecta", "sem internet", "caiu",
                     "roteador", "wi-fi", "wifi", "lentidao", "instabilidade", "travando",
                     "nao funciona", "sem conexao", "muito lenta"],
    },
    "portabilidade": {
        "label": "Portabilidade", "area": Area.vendas,
        "keywords": ["portabilidade", "portar", "trazer meu numero", "mudar de operadora"],
    },
    "cancelamento": {
        "label": "Cancelamento", "area": Area.retencao,
        "keywords": ["cancelar", "encerrar contrato", "desistir", "quero sair", "rescindir",
                     "nao estou satisfeito"],
    },
    "falar_atendente": {
        "label": "Falar com Atendente", "area": Area.suporte,
        "keywords": ["falar com atendente", "quero um humano", "atendente", "falar com alguem",
                     "pessoa de verdade", "nao quero robo"],
    },
    "consulta_informacao": {
        "label": "Consulta de Informação", "area": Area.marketing,
        "keywords": ["quanto custa", "quais planos", "saber mais", "promocao", "como funciona",
                     "planos familia", "duvida"],
    },
}

PLAN_RE = re.compile(r"(?:claro\s+)?flex\s*(\d{2,3})\s*gb", re.IGNORECASE)
MONEY_RE = re.compile(r"r\$\s*([\d.,]+)", re.IGNORECASE)


def normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def extract_entities(text: str) -> dict:
    entities: dict = {}
    if m := PLAN_RE.search(text):
        entities["plano"] = f"Claro Flex {m.group(1)}GB"
    if m := MONEY_RE.search(text):
        entities["valor"] = m.group(1)
    return entities


class RuleBasedIntentClassifier(IntentClassifier):
    @property
    def engine_name(self) -> str:
        return "rules"

    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent:
        norm = normalize(text)
        scores: dict[str, float] = {}

        for slug, spec in TAXONOMY.items():
            weight = 0.0
            for keyword in spec["keywords"]:
                if normalize(keyword) in norm:
                    weight += 0.30 + min(len(keyword), 24) / 100
            if weight:
                scores[slug] = min(0.52 + weight, 0.97)

        entities = extract_entities(text)
        if not scores:
            return UNIDENTIFIED.model_copy(update={"entities": entities})

        slug = max(scores, key=scores.get)
        spec = TAXONOMY[slug]
        return Intent(
            slug=slug, name=spec["label"], confidence=round(scores[slug], 2),
            area=spec["area"], entities=entities, engine=IntentEngine.rules,
            reasoning=f"Palavra-chave da taxonomia entre {len(scores)} candidata(s).",
        )
