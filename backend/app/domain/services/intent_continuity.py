"""Servico de dominio: continuidade da intencao entre turnos.

Numa conversa aberta, "pode prosseguir" nao tem palavra-chave nenhuma -- mas
tampouco muda de assunto. Tratar cada mensagem como se fosse a primeira e
justamente o comportamento que faz o cliente sentir que precisa se repetir.

A regra: mensagem de baixa confianca dentro de uma conversa que ja tem intencao
firmada herda essa intencao. Uma classificacao nova so prevalece quando vier
com confianca suficiente para valer a mudanca de assunto.
"""
from __future__ import annotations

from ..value_objects import Intent

# Intencoes meta: dizem o que fazer com a conversa, nao sobre o que ela e.
META_INTENTS = {"falar_atendente", "nao_identificada"}


class IntentContinuityService:
    def __init__(self, minimum_confidence: float = 0.55) -> None:
        self._minimum = minimum_confidence

    def reconcile(self, fresh: Intent, previous: Intent | None) -> Intent:
        """Decide qual intencao governa este turno."""
        if previous is None or previous.slug in META_INTENTS:
            return fresh

        if fresh.confidence >= self._minimum and fresh.slug != "nao_identificada":
            return fresh

        # herda o assunto, preservando qualquer entidade nova que tenha aparecido
        return previous.model_copy(update={
            "entities": {**previous.entities, **fresh.entities},
            "reasoning": (f"Assunto herdado da conversa em andamento "
                          f"(mensagem atual sem sinal próprio: {fresh.confidence:.0%})."),
        })

    @staticmethod
    def governs_business_area(intent: Intent) -> bool:
        """Intencao meta nao redefine a area da conversa: pedir atendente nao
        transforma um caso de vendas em suporte."""
        return intent.slug not in META_INTENTS
