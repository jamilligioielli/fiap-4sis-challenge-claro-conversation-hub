"""Casos de uso do Console de Operação.

São os que alimentam as telas do front-end: fila do Inbox, Conversa Ativa,
transferência para atendente e resposta do agente. Ficam separados da ingestão
porque têm outro ator (o atendente, não o cliente) e outro ciclo de vida.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ...domain.entities.conversation import Conversation
from ...domain.entities.message import Message
from ...domain.ports.audit_log import AuditLog
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository
from ...domain.value_objects.author import Author
from ...domain.value_objects.channel import Channel
from ...domain.value_objects.clock import utcnow
from ..dto.conversation_detail import ConversationDetail
from ..dto.list_conversations_query import ListConversationsQuery


def relative_label(moment: datetime) -> str:
    """'Há 2 min' — a fila do atendente pensa em tempo decorrido, não em relógio."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    minutes = int((utcnow() - moment).total_seconds() // 60)
    if minutes < 1:
        return "Agora"
    if minutes < 60:
        return f"Há {minutes} min"
    hours, rest = divmod(minutes, 60)
    if hours < 24:
        return f"Há {hours}h" + (f" {rest}min" if rest else "")
    return f"Há {hours // 24}d"


# ------------------------------------------------------------------ listagem
class ListConversationsUseCase:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def execute(self, query: ListConversationsQuery) -> list[Conversation]:
        items = await self._conversations.list(
            area=query.area, channel=query.channel, status=query.status)
        if query.search:
            needle = query.search.lower()
            items = [c for c in items
                     if needle in c.customer_name.lower() or needle in c.last_message.lower()]
        return items


# ------------------------------------------------------------------- detalhe
class GetConversationUseCase:
    def __init__(self, conversations: ConversationRepository,
                 customers: CustomerRepository, audit: AuditLog) -> None:
        self._conversations = conversations
        self._customers = customers
        self._audit = audit

    async def execute(self, conversation_id: str) -> ConversationDetail | None:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            return None

        messages = await self._conversations.transcript(conversation_id)
        customer = await self._customers.get(conversation.customer_id)
        await self._audit.record("conversation.viewed", conversation.customer_id,
                                 {"conversation_id": conversation_id})

        return ConversationDetail(
            conversation=conversation,
            messages=messages,
            summary=self._summarize(conversation, messages, customer),
            suggestions=self._suggest(conversation, customer),
            insights=self._insights(customer),
        )

    @staticmethod
    def _summarize(conversation: Conversation, messages: list[Message], customer) -> dict:
        channels = " → ".join(c.label for c in conversation.channels_used)
        wanted = (conversation.intent.entities.get("plano")
                  if conversation.intent else None)
        request = conversation.intent.name if conversation.intent else "Não classificada"
        if wanted:
            request = f"{request} para {wanted}"
        return {
            "cliente": conversation.customer_name or "Não identificado",
            "solicitacao": request,
            "plano_atual": (f"{customer.plan.name} (R$ {customer.plan.price:.2f})".replace(".", ",")
                            if customer and customer.plan else "—"),
            "status": ("Transferida para atendente" if conversation.handover.requested
                       else "Em atendimento automatizado"),
            "canal": channels or "—",
            "mensagens": str(len(messages)),
        }

    @staticmethod
    def _suggest(conversation: Conversation, customer) -> list[str]:
        slug = conversation.intent.slug if conversation.intent else ""
        if slug == "alteracao_plano":
            return ["Confirmar dados cadastrais antes de prosseguir",
                    "Oferecer plano Claro Flex 60GB por R$ 109,90 (upgrade)",
                    "Informar sobre combo família com desconto"]
        if slug == "cancelamento":
            return ["Entender o motivo do cancelamento antes de qualquer oferta",
                    "Verificar histórico de incidentes técnicos do cliente",
                    "Avaliar oferta de retenção compatível com o perfil"]
        if slug == "suporte_tecnico":
            return ["Confirmar se o diagnóstico automático já foi apresentado",
                    "Verificar incidentes na região do cliente",
                    "Avaliar necessidade de visita técnica"]
        if slug == "segunda_via_fatura":
            return ["Enviar a segunda via pelo canal preferido do cliente",
                    "Confirmar se o vencimento atual atende o cliente"]
        return ["Confirmar a necessidade do cliente antes de agir",
                "Consultar o contexto completo do cliente"]

    @staticmethod
    def _insights(customer) -> list[dict]:
        if customer is None:
            return []
        insights = []
        if customer.plan and customer.plan.usage_percent >= 80:
            insights.append({"text": f"Usa {customer.plan.usage_percent}% da franquia mensal",
                             "tone": "warning"})
            insights.append({"text": "Alta propensão a upgrade", "tone": "positive"})
        if customer.segment == "VIP":
            insights.append({"text": f"Cliente {customer.segment} desde {customer.customer_since}",
                             "tone": "info"})
        insights.append({"text": f"Risco de churn: {customer.churn_label.lower()}"
                                 f" ({customer.churn_risk:.0%})",
                         "tone": "positive" if customer.churn_risk < 0.25 else "warning"})
        return insights


# ------------------------------------------------------------------ handover
class RequestHandoverUseCase:
    """Acionado pelo console quando o atendente puxa a conversa para si."""

    def __init__(self, conversations: ConversationRepository, audit: AuditLog) -> None:
        self._conversations = conversations
        self._audit = audit

    async def execute(self, conversation_id: str, reason: str,
                      agent: str | None = None) -> Conversation | None:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            return None

        transcript = await self._conversations.transcript(conversation_id)
        conversation.request_handover(reason, conversation.handover.services_consulted,
                                      len(transcript))
        if agent:
            conversation.assign_agent(agent)

        await self._conversations.add_message(Message(
            conversation_id=conversation_id, author=Author.system,
            text=f"Conversa transferida para atendimento humano — {reason}",
        ))
        await self._conversations.save(conversation)
        await self._audit.record("handover.assigned", conversation.customer_id,
                                 {"conversation_id": conversation_id, "agent": agent})
        return conversation


# --------------------------------------------------------------- resposta do agente
class ReplyAsAgentUseCase:
    def __init__(self, conversations: ConversationRepository, audit: AuditLog) -> None:
        self._conversations = conversations
        self._audit = audit

    async def execute(self, conversation_id: str, text: str,
                      channel: Channel | None = None) -> Message | None:
        conversation = await self._conversations.get(conversation_id)
        if conversation is None:
            return None

        target = channel or (conversation.channels_used[-1]
                             if conversation.channels_used else Channel.web)
        message = Message(conversation_id=conversation_id, author=Author.agent,
                          text=text, channel=target)
        await self._conversations.add_message(message)

        conversation.record_message(text, target, from_customer=False)
        await self._conversations.save(conversation)
        await self._audit.record("agent.replied", conversation.customer_id,
                                 {"conversation_id": conversation_id})
        return message
