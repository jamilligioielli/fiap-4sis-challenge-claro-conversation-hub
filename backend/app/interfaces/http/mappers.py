"""Tradução domínio -> DTO de API. Concentrada aqui para que nenhum router
precise conhecer a forma interna das entidades."""
from __future__ import annotations

from ...application.use_cases.console import relative_label
from ...domain.entities import Conversation, Customer, Message
from ...domain.value_objects import Intent
from .schemas import (ConversationListItem, CustomerContextResponse, IntentResponse,
                      MessageResponse, PlanResponse)


def intent_to_dto(intent: Intent | None) -> IntentResponse | None:
    if intent is None:
        return None
    return IntentResponse(
        slug=intent.slug, name=intent.name, confidence=intent.confidence,
        confidence_label=intent.confidence_label, area=intent.area,
        entities=intent.entities, engine=intent.engine.value, reasoning=intent.reasoning,
    )


def conversation_to_list_item(conversation: Conversation) -> ConversationListItem:
    channels = conversation.channels_used
    return ConversationListItem(
        id=conversation.id,
        customer_id=conversation.customer_id,
        customer_name=conversation.customer_name or "Cliente não identificado",
        channel=channels[-1] if channels else "web",
        channels_used=channels,
        status=conversation.status,
        last_message=conversation.last_message,
        timestamp=relative_label(conversation.updated_at),
        updated_at=conversation.updated_at,
        priority=conversation.priority,
        area=conversation.area,
        unread=conversation.unread,
        intent=conversation.intent.name if conversation.intent else None,
        confidence=conversation.intent.confidence if conversation.intent else None,
        handover_requested=conversation.handover.requested,
    )


def message_to_dto(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id, author=message.author, text=message.text,
        channel=message.channel, timestamp=message.timestamp,
        intent=intent_to_dto(message.intent),
    )


def customer_to_dto(customer: Customer, conversations: list[Conversation],
                    upgrades: list[dict]) -> CustomerContextResponse:
    used: list = []
    for conversation in conversations:
        for channel in conversation.channels_used:
            if channel not in used:
                used.append(channel)

    plan = None
    if customer.plan:
        plan = PlanResponse(
            name=customer.plan.name, price=customer.plan.price,
            data_gb=customer.plan.data_gb, used_gb=customer.plan.used_gb,
            usage_percent=customer.plan.usage_percent, line=customer.plan.line,
            due_day=customer.plan.due_day, status=customer.plan.status,
        )

    return CustomerContextResponse(
        id=customer.id, name=customer.name, document_masked=customer.document_masked,
        birth_date=customer.birth_date, customer_since=customer.customer_since,
        segment=customer.segment, email=customer.email, phone=customer.phone,
        preferred_channel=customer.preferred_channel, plan=plan,
        products=customer.products,
        timeline=[t.model_dump() for t in customer.timeline],
        churn_risk=customer.churn_risk, churn_label=customer.churn_label,
        churn_factors=customer.churn_factors, upgrade_options=upgrades,
        conversation_count=len(conversations), channels_used=used,
    )
