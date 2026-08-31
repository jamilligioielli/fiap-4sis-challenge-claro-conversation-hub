"""Conversa — agregado raiz do domínio."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..value_objects.area import Area
from ..value_objects.channel import Channel
from ..value_objects.clock import utcnow
from ..value_objects.conversation_status import ConversationStatus
from ..value_objects.intent import Intent
from ..value_objects.priority import Priority
from .handover import Handover
from .identifiers import new_id


class Conversation(BaseModel):
    """Mensagens, canais usados e estado de transferência só mudam através
    daqui. As invariantes ficam nos métodos, nunca espalhadas pelos casos de uso."""

    id: str = Field(default_factory=lambda: new_id("conv"))
    session_id: str
    customer_id: str
    customer_name: str = ""
    status: ConversationStatus = ConversationStatus.active
    area: Area = Area.suporte
    priority: Priority = Priority.medium
    channels_used: list[Channel] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_message: str = ""
    unread: bool = False
    intent: Intent | None = None
    handover: Handover = Field(default_factory=Handover)
    initiated_by_company: bool = Field(
        default=False,
        description="Verdadeiro quando a Claro iniciou o contato, e não o cliente.",
    )

    # -- invariantes ------------------------------------------------------
    def apply_intent(self, intent: Intent, governs_area: bool = True) -> None:
        """`governs_area=False` para intenções meta: pedir atendente não
        transforma um caso de Vendas num caso de Suporte."""
        self.intent = intent
        if governs_area:
            self.area = intent.area
        if intent.slug in ("cancelamento", "falar_atendente"):
            self.priority = Priority.high
        elif intent.confidence < 0.5:
            self.priority = Priority.high
        self.updated_at = utcnow()

    def record_message(self, text: str, channel: Channel, from_customer: bool) -> None:
        self.last_message = text
        self.unread = from_customer
        if channel not in self.channels_used:
            self.channels_used.append(channel)
        self.updated_at = utcnow()

    def request_handover(self, reason: str, services: list[str],
                         transcript_size: int) -> None:
        """Uma conversa transferida não volta sozinha ao assistente: quem devolve
        é o atendente, explicitamente."""
        if self.status is ConversationStatus.transferred:
            return
        self.status = ConversationStatus.transferred
        self.handover = Handover(
            requested=True, reason=reason, requested_at=utcnow(),
            services_consulted=services, transcript_size=transcript_size,
        )
        self.priority = Priority.high
        self.updated_at = utcnow()

    def assign_agent(self, agent: str) -> None:
        if not self.handover.requested:
            raise ValueError("Não é possível atribuir atendente sem transferência solicitada.")
        self.handover.assigned_agent = agent
        self.updated_at = utcnow()

    def close(self) -> None:
        self.status = ConversationStatus.pending
        self.updated_at = utcnow()

    # -- consultas --------------------------------------------------------
    @property
    def is_open(self) -> bool:
        """Conduzida pelo assistente."""
        return self.status in (ConversationStatus.active, ConversationStatus.waiting)

    @property
    def is_current(self) -> bool:
        """Ainda é a conversa vigente do cliente — inclusive já transferida.

        Depois da transferência o cliente continua escrevendo, e essas mensagens
        têm de chegar ao atendente que assumiu o caso.
        """
        return self.status is not ConversationStatus.pending

    @property
    def with_human(self) -> bool:
        return self.status is ConversationStatus.transferred

    @property
    def subject(self) -> str:
        return self.intent.name if self.intent else "assunto ainda não identificado"
