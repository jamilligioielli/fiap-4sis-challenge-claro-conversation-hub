"""Caso de uso: visao 360 do cliente (tela Contexto do Cliente).

Todo acesso passa pela trilha de auditoria: consultar dado de cliente e um
evento auditavel, nao uma leitura silenciosa ( / LGPD).
"""
from __future__ import annotations

from dataclasses import dataclass

from ...domain.entities import Conversation, Customer
from ...domain.ports import AuditLog, ConversationRepository, CustomerRepository


@dataclass
class CustomerContext:
    customer: Customer
    conversations: list[Conversation]
    upgrade_options: list[dict]


class GetCustomerContextUseCase:
    def __init__(self, customers: CustomerRepository, conversations: ConversationRepository,
                 backends, audit: AuditLog) -> None:
        self._customers = customers
        self._conversations = conversations
        self._backends = backends
        self._audit = audit

    async def execute(self, customer_id: str) -> CustomerContext | None:
        customer = await self._customers.get(customer_id)
        if customer is None:
            return None

        await self._audit.record("customer.context.viewed", customer_id, {})

        history = await self._conversations.list(customer_id=customer_id)
        catalog = await self._backends.call(
            "catalogo_planos",
            current_plan=customer.plan.name if customer.plan else None,
        )

        upgrades = catalog.get("upgrades", [])
        for index, option in enumerate(upgrades):
            option["status"] = "Recomendado" if index == 0 else "Disponível"

        return CustomerContext(customer=customer, conversations=history,
                               upgrade_options=upgrades)
