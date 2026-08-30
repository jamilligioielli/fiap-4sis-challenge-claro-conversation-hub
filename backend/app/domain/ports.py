"""Portas do dominio (Ports & Adapters).

Sao as interfaces que o dominio e os casos de uso conhecem. Toda implementacao
concreta -- Redis, MongoDB, Groq, mocks -- vive em infrastructure/ e depende
destas abstracoes, nunca o contrario (Dependency Inversion).

Trocar MongoDB por Postgres, ou Groq por OpenAI, e escrever outro adaptador.
Nenhum caso de uso muda.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import Conversation, Customer, Message, Session
from .studio import StudioConfig
from .value_objects import Channel, Intent


class SessionRepository(ABC):
    """Contexto de curto prazo (Redis)."""

    @abstractmethod
    async def get(self, session_id: str) -> Session | None: ...

    @abstractmethod
    async def save(self, session: Session) -> None: ...

    @abstractmethod
    async def resolve_alias(self, channel: str, external_id: str) -> str | None: ...

    @abstractmethod
    async def bind_alias(self, channel: str, external_id: str, customer_id: str) -> None: ...

    @abstractmethod
    async def health(self) -> str: ...


class ConversationRepository(ABC):
    """Historico de longo prazo (MongoDB)."""

    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    async def save(self, conversation: Conversation) -> None: ...

    @abstractmethod
    async def list(self, *, customer_id: str | None = None, area: str | None = None,
                   channel: str | None = None, status: str | None = None) -> list[Conversation]: ...

    @abstractmethod
    async def open_for_customer(self, customer_id: str) -> Conversation | None: ...

    @abstractmethod
    async def add_message(self, message: Message) -> None: ...

    @abstractmethod
    async def transcript(self, conversation_id: str) -> list[Message]: ...

    @abstractmethod
    async def health(self) -> str: ...


class CustomerRepository(ABC):
    @abstractmethod
    async def get(self, customer_id: str) -> Customer | None: ...

    @abstractmethod
    async def find_by_alias(self, channel: str, external_id: str) -> Customer | None: ...

    @abstractmethod
    async def save(self, customer: Customer) -> None: ...


class StudioConfigRepository(ABC):
    @abstractmethod
    async def get(self) -> StudioConfig: ...

    @abstractmethod
    async def save(self, config: StudioConfig) -> StudioConfig: ...


class AuditLog(ABC):
    """Trilha de auditoria de acesso a dado pessoal (RNF003 / LGPD)."""

    @abstractmethod
    async def record(self, action: str, customer_id: str | None, detail: dict) -> None: ...

    @abstractmethod
    async def list(self, customer_id: str | None = None, limit: int = 50) -> list[dict]: ...


class IntentClassifier(ABC):
    """Porta do RF002. O caso de uso nao sabe se atras disto ha um LLM ou
    um classificador por regras."""

    @abstractmethod
    async def classify(self, text: str, *, history: list[str] | None = None) -> Intent: ...

    @property
    @abstractmethod
    def engine_name(self) -> str: ...


class BackendSystems(ABC):
    """Porta dos sistemas internos da Claro. Hoje atendida por mocks; em
    producao, pelas integracoes reais -- sem alteracao no nucleo."""

    @abstractmethod
    async def call(self, service: str, **kwargs) -> dict: ...

    @property
    @abstractmethod
    def available(self) -> list[str]: ...


class OutboundGateway(ABC):
    """Porta de saída para um canal externo.

    O hub responde de duas formas conforme o canal: síncrona, quando o canal
    chama a API e lê a resposta na mesma requisição (site, app, simulador); e
    assíncrona, quando o canal entrega por webhook e a resposta precisa ser
    empurrada de volta por outra chamada (WhatsApp). Esta porta cobre o segundo
    caso — e é o que um canal novo do mesmo feitio vai implementar.
    """

    channel: "Channel"
    enabled: bool

    @abstractmethod
    async def send(self, to: str, text: str) -> dict:
        """Entrega uma mensagem ao cliente. `to` é o endereço no canal."""
