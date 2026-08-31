"""Lista de clientes disponíveis para simulação."""
from __future__ import annotations

from ...domain.entities.customer import Customer
from ...domain.ports.conversation_repository import ConversationRepository
from ...domain.ports.customer_repository import CustomerRepository


class ListCustomersUseCase:
    """Alimenta a tela de escolha de persona do simulador: quem existe, como
    cada um se comporta e se já há conversa em andamento."""

    def __init__(self, customers: CustomerRepository,
                 conversations: ConversationRepository) -> None:
        self._customers = customers
        self._conversations = conversations

    async def execute(self) -> list[tuple[Customer, int, str | None]]:
        result: list[tuple[Customer, int, str | None]] = []
        for customer in await self._customers.all():
            history = await self._conversations.list(customer_id=customer.id)
            current = next((c.id for c in history if c.is_current), None)
            result.append((customer, len(history), current))
        return sorted(result, key=lambda item: item[0].name)
