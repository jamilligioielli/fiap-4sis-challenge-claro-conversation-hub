"""Entidades e agregados do dominio.

Conversation e o agregado raiz: mensagens, canais usados e estado de handover
so mudam atraves dele. As invariantes ficam nos metodos da propria entidade --
nunca espalhadas pelos casos de uso.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .value_objects import (Area, Author, Channel, Consent, ConversationStatus,
                            Intent, Priority, utcnow)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


# --------------------------------------------------------------------- evento
class ConversationEvent(BaseModel):
    """RF001 -- o schema unico de evento conversacional.

    Qualquer canal, ao entrar no hub, produz exatamente esta forma. Depois deste
    ponto o nucleo nao sabe -- nem precisa saber -- de onde a mensagem veio.
    """
    event_id: str = Field(default_factory=lambda: new_id("evt"))
    occurred_at: datetime = Field(default_factory=utcnow)
    channel: Channel
    customer_id: str
    session_id: str
    conversation_id: str
    author: Author
    text: str
    consent: Consent = Field(default_factory=Consent)
    metadata: dict = Field(default_factory=dict)


# ------------------------------------------------------------------- mensagem
class Message(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    conversation_id: str
    author: Author
    text: str
    channel: Channel | None = None
    timestamp: datetime = Field(default_factory=utcnow)
    intent: Intent | None = None


# ------------------------------------------------------------------- handover
class Handover(BaseModel):
    """RF005 -- o pacote que atravessa a fronteira bot -> humano."""
    requested: bool = False
    reason: str | None = None
    requested_at: datetime | None = None
    assigned_agent: str | None = None
    services_consulted: list[str] = Field(default_factory=list)
    transcript_size: int = 0


# --------------------------------------------------------------- sessao viva
class Session(BaseModel):
    """Contexto de curto prazo. Vive no Redis com TTL."""
    session_id: str = Field(default_factory=lambda: new_id("ses"))
    conversation_id: str
    customer_id: str
    channels_used: list[Channel] = Field(default_factory=list)
    turns: int = 0
    services_consulted: list[str] = Field(default_factory=list)
    last_intent: Intent | None = None
    consecutive_low_confidence: int = 0

    def register_classification(self, confident: bool) -> int:
        """Conta quantas mensagens seguidas o hub não conseguiu entender.

        Uma mensagem sem sinal próprio dentro de um assunto firmado é normal
        ('pode prosseguir'). Três seguidas já são um cliente sendo mal atendido,
        e aí o transbordo se justifica.
        """
        self.consecutive_low_confidence = 0 if confident else self.consecutive_low_confidence + 1
        return self.consecutive_low_confidence

    def register_channel(self, channel: Channel) -> bool:
        """Registra o canal e diz se houve troca em relacao ao anterior."""
        switched = bool(self.channels_used) and self.channels_used[-1] != channel
        if channel not in self.channels_used:
            self.channels_used.append(channel)
        elif switched:
            self.channels_used.remove(channel)
            self.channels_used.append(channel)
        return switched

    def previous_channel(self) -> Channel | None:
        return self.channels_used[-2] if len(self.channels_used) > 1 else None


# ------------------------------------------------------ agregado: conversa
class Conversation(BaseModel):
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

    # -- invariantes do agregado ------------------------------------------
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
        """Uma conversa transferida nunca volta sozinha ao bot: quem devolve e
        o atendente, explicitamente."""
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
            raise ValueError("Não é possível atribuir atendente sem handover solicitado.")
        self.handover.assigned_agent = agent
        self.updated_at = utcnow()

    @property
    def is_open(self) -> bool:
        """Conduzida pelo bot."""
        return self.status in (ConversationStatus.active, ConversationStatus.waiting)

    @property
    def is_current(self) -> bool:
        """Ainda é a conversa vigente do cliente — inclusive já transferida.

        A distinção importa: depois do transbordo o cliente continua escrevendo,
        e essas mensagens têm de chegar ao atendente que assumiu o caso. Abrir
        uma conversa nova ali perderia justamente o que o RF005 promete.
        """
        return self.status is not ConversationStatus.pending

    @property
    def with_human(self) -> bool:
        return self.status is ConversationStatus.transferred


# ------------------------------------------------------------------- cliente
class Plan(BaseModel):
    name: str
    price: float
    data_gb: int
    used_gb: float = 0.0
    line: str = ""
    due_day: int = 10
    status: str = "Ativo"

    @property
    def usage_percent(self) -> int:
        return round(self.used_gb / self.data_gb * 100) if self.data_gb else 0


class TimelineEvent(BaseModel):
    date: str
    event: str
    type: str


class Customer(BaseModel):
    id: str
    name: str
    document_masked: str = ""
    birth_date: str = ""
    customer_since: str = ""
    segment: str = "Padrão"
    email: str = ""
    phone: str = ""
    preferred_channel: Channel = Channel.whatsapp
    plan: Plan | None = None
    products: list[dict] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    churn_risk: float = 0.0
    churn_factors: list[dict] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)

    @property
    def first_name(self) -> str:
        return self.name.split(" ")[0] if self.name else ""

    @property
    def churn_label(self) -> str:
        if self.churn_risk < 0.25:
            return "Baixo"
        return "Médio" if self.churn_risk < 0.6 else "Alto"
