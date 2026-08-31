"""Tradução entre o domínio e os DTOs da API.

Concentrada aqui para que nenhuma rota precise conhecer a forma interna das
entidades.
"""
from __future__ import annotations

from ...application.use_cases.console import relative_label
from ...domain.entities.conversation import Conversation
from ...domain.entities.customer import Customer
from ...domain.entities.message import Message
from ...domain.outreach.eligibility import EligibleCustomer
from ...domain.value_objects.intent import Intent
from .schemas.conversation_list_item import ConversationListItem
from .schemas.customer_context_response import CustomerContextResponse
from .schemas.customer_summary_response import CustomerSummaryResponse
from .schemas.eligible_customer_response import EligibleCustomerResponse
from .schemas.intent_response import IntentResponse
from .schemas.message_response import MessageResponse
from .schemas.plan_response import PlanResponse


def intent_to_dto(intent: Intent | None) -> IntentResponse | None:
    if intent is None:
        return None
    return IntentResponse(
        slug=intent.slug, name=intent.name, confidence=intent.confidence,
        confidence_label=intent.confidence_label, area=intent.area,
        entities=intent.entities, engine=intent.engine.value, reasoning=intent.reasoning,
    )


def conversation_to_list_item(conversation: Conversation,
                              message_count: int = 0) -> ConversationListItem:
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
        started_at=conversation.started_at,
        priority=conversation.priority,
        area=conversation.area,
        unread=conversation.unread,
        intent=conversation.intent.name if conversation.intent else None,
        confidence=conversation.intent.confidence if conversation.intent else None,
        handover_requested=conversation.handover.requested,
        initiated_by_company=conversation.initiated_by_company,
        message_count=message_count,
        nps_score=conversation.nps.score if conversation.nps else None,
        nps_category=conversation.nps.category if conversation.nps else None,
        closed_by=conversation.nps.closed_by if conversation.nps else None,
    )


def message_to_dto(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id, author=message.author, text=message.text,
        channel=message.channel, timestamp=message.timestamp,
        intent=intent_to_dto(message.intent),
        source=message.source.value if message.source else None,
    )


def customer_to_summary(customer: Customer, conversation_count: int,
                        open_conversation_id: str | None) -> CustomerSummaryResponse:
    return CustomerSummaryResponse(
        id=customer.id, name=customer.name, segment=customer.segment,
        persona_summary=customer.persona_summary,
        preferred_channel=customer.preferred_channel,
        plan_name=customer.plan.name if customer.plan else None,
        plan_usage_percent=customer.plan.usage_percent if customer.plan else None,
        churn_label=customer.churn_label,
        marketing_opt_in=customer.marketing_opt_in,
        conversation_count=conversation_count,
        open_conversation_id=open_conversation_id,
    )


def customer_to_context(customer: Customer, conversations: list[Conversation],
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
        preferred_channel=customer.preferred_channel,
        persona_summary=customer.persona_summary,
        marketing_opt_in=customer.marketing_opt_in,
        plan=plan, products=customer.products,
        timeline=[t.model_dump() for t in customer.timeline],
        churn_risk=customer.churn_risk, churn_label=customer.churn_label,
        churn_factors=customer.churn_factors, upgrade_options=upgrades,
        conversation_count=len(conversations), channels_used=used,
    )


def eligible_to_dto(item: EligibleCustomer) -> EligibleCustomerResponse:
    return EligibleCustomerResponse(
        customer_id=item.customer_id,
        customer_name=item.customer_name,
        segment=item.segment,
        score=item.score,
        reasons=[r.model_dump() for r in item.reasons],
        blocks=[b.model_dump() for b in item.blocks],
        suggested_offer=item.suggested_offer.model_dump() if item.suggested_offer else None,
        window_open=item.window_open,
        window_hours_remaining=item.window_hours_remaining,
        marketing_opt_in=item.marketing_opt_in,
        can_contact=item.can_contact,
        requires_template=item.requires_template,
    )
