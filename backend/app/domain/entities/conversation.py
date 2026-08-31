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
from .nps_survey import NpsSurvey


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
    nps: NpsSurvey | None = Field(
        default=None,
        description="Pesquisa disparada no encerramento. Presente e sem nota "
                    "significa que o cliente não respondeu.",
    )
    closed_at: datetime | None = None

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

    def close(self, closed_by: str = "bot", with_survey: bool = False) -> None:
        """Encerra o atendimento e, opcionalmente, abre a pesquisa.

        Quem encerra é registrado porque a leitura da nota depende disso: um 6
        depois de um humano assumir conta uma história diferente de um 6 que o
        assistente resolveu sozinho.
        """
        if self.status is ConversationStatus.pending:
            return
        self.closed_at = utcnow()
        self.updated_at = self.closed_at

        # Com pesquisa, o atendimento acabou mas a conversa não: ela fica em
        # espera para receber a nota. Fechá-la aqui faria a resposta do cliente
        # abrir uma conversa nova, e a nota se perderia do atendimento que a
        # motivou — que é justamente o que dá sentido à nota.
        if with_survey and self.nps is None:
            self.nps = NpsSurvey(closed_by=closed_by)
            self.status = ConversationStatus.waiting
        else:
            self.status = ConversationStatus.pending

    def record_nps(self, score: int, comment: str = "") -> None:
        if self.nps is None:
            raise ValueError("Não há pesquisa aberta nesta conversa.")
        self.nps.record(score, comment)
        self.status = ConversationStatus.pending
        self.updated_at = utcnow()

    def dismiss_nps(self) -> None:
        """O cliente não quis dar nota. A conversa encerra do mesmo jeito —
        insistir seria transformar a pesquisa em incômodo."""
        if self.nps is not None:
            self.nps.attempts += 1
            self.nps.dismissed = True
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
    def awaiting_nps(self) -> bool:
        """Pesquisa enviada, sem nota e ainda aberta.

        Difere de "sem nota": uma pesquisa recusada também fica sem nota, e ali
        o hub já parou de perguntar. Confundir os dois faria o assistente ler a
        próxima mensagem do cliente como nota para sempre.
        """
        return self.nps is not None and self.nps.open

    @property
    def subject(self) -> str:
        return self.intent.name if self.intent else "assunto ainda não identificado"
