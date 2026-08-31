"""Porta do cadastro de clientes."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..entities.customer import Customer


class CustomerRepository(ABC):
    @abstractmethod
    async def get(self, customer_id: str) -> Customer | None: ...

    @abstractmethod
    async def find_by_alias(self, channel: str, external_id: str) -> Customer | None: ...

    @abstractmethod
    async def save(self, customer: Customer) -> None: ...

    @abstractmethod
    async def all(self) -> list[Customer]: ...
