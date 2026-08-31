"""Servico de dominio: politica de transbordo.

Concentra a decisao de quando a conversa deve sair do bot. Estar num unico
lugar permite auditar e ajustar o criterio sem cacar `if` espalhado pelo codigo.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..entities import Conversation
from ..value_objects import Intent

SENTIMENT_TRIGGERS = (
    "nao aguento", "absurdo", "pessimo", "ridiculo", "processar",
    "procon", "cancelar tudo", "inaceitavel",
)


@dataclass(frozen=True)
class HandoverDecision:
    should_handover: bool
    reason: str | None = None


class HandoverPolicy:
    def __init__(self, confidence_threshold: float = 0.55) -> None:
        self._threshold = confidence_threshold

    @property
    def confidence_threshold(self) -> float:
        return self._threshold

    def evaluate(self, intent: Intent, text: str, conversation: Conversation,
                 consecutive_failures: int = 0) -> HandoverDecision:
        if intent.slug == "falar_atendente":
            return HandoverDecision(True, "Cliente solicitou falar com atendente")

        lowered = text.lower()
        if any(t in lowered for t in SENTIMENT_TRIGGERS):
            return HandoverDecision(True, "Insatisfação detectada na mensagem do cliente")

        # Não entender *uma* mensagem não é motivo para desistir do cliente: o
        # assistente pergunta o que ele quis dizer e tenta de novo. Escalar no
        # primeiro tropeço transformaria o hub num encaminhador de fila — e
        # deixaria o contador de tentativas abaixo sem efeito nenhum, já que a
        # primeira falha nunca chegaria à segunda.
        if consecutive_failures >= 3:
            return HandoverDecision(True, "Três tentativas sem compreensão da solicitação")

        if intent.confidence < self._threshold and consecutive_failures >= 2:
            return HandoverDecision(
                True, f"Baixa confiança na classificação ({intent.confidence:.0%}) "
                      f"após {consecutive_failures} tentativas")

        if intent.slug == "cancelamento" and conversation.priority.value == "high":
            return HandoverDecision(True, "Pedido de cancelamento encaminhado à retenção")

        return HandoverDecision(False)
