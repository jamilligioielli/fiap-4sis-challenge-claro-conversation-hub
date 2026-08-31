"""Servico de dominio: roteamento por intencao.

Decide, a partir da intencao, qual fluxo de negocio roda e quais sistemas
internos precisam ser consultados. Nao executa nada -- so decide. A execucao
fica no caso de uso, que tem as portas em maos.

Manter a decisao separada da execucao torna esta regra testavel sem nenhum
mock de infraestrutura.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..value_objects import Intent


class Flow(str, Enum):
    venda = "venda"
    suporte = "suporte"
    financeiro = "financeiro"
    retencao = "retencao"
    informacao = "informacao"
    handover = "handover"
    fallback = "fallback"


@dataclass(frozen=True)
class Route:
    flow: Flow
    services: tuple[str, ...]


_TABLE: dict[str, Route] = {
    "alteracao_plano":     Route(Flow.venda,      ("crm", "catalogo_planos")),
    "portabilidade":       Route(Flow.venda,      ("catalogo_planos",)),
    "segunda_via_fatura":  Route(Flow.financeiro, ("faturamento",)),
    "suporte_tecnico":     Route(Flow.suporte,    ("diagnostico_tecnico",)),
    "cancelamento":        Route(Flow.retencao,   ("crm", "catalogo_planos")),
    "consulta_informacao": Route(Flow.informacao, ("catalogo_planos",)),
    "falar_atendente":     Route(Flow.handover,   ()),
}

_FALLBACK = Route(Flow.fallback, ())


class RoutingService:
    @staticmethod
    def route(intent: Intent) -> Route:
        """Intencao de baixa confianca nao aciona sistema interno nenhum:
        agir sobre um palpite ruim custa mais caro do que perguntar de novo."""
        if not intent.is_confident:
            return _FALLBACK
        return _TABLE.get(intent.slug, _FALLBACK)

    @staticmethod
    def known_intents() -> list[str]:
        return list(_TABLE)
