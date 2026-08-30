"""Composition root.

Único lugar do sistema onde implementações concretas são escolhidas e ligadas às
portas. Todo o resto do código depende de abstrações; a decisão de "Redis ou
memória", "Groq ou regras", "Mongo ou memória" é tomada aqui e em nenhum outro
lugar (Dependency Inversion, na prática).

Trocar de infraestrutura é editar este arquivo — nenhum caso de uso muda.
"""
from __future__ import annotations

import logging

from .application.use_cases.console import (GetConversationUseCase, ListConversationsUseCase,
                                            ReplyAsAgentUseCase, RequestHandoverUseCase)
from .application.use_cases.customer_context import GetCustomerContextUseCase
from .application.use_cases.dashboard import GetDashboardMetricsUseCase
from .application.use_cases.ingest_message import IngestMessageUseCase
from .application.use_cases.studio_config import (GetStudioConfigUseCase,
                                                  UpdateChannelConfigUseCase,
                                                  UpdateStudioConfigUseCase)
from .domain.ports import (AuditLog, BackendSystems, ConversationRepository,
                           CustomerRepository, IntentClassifier, SessionRepository,
                           StudioConfigRepository)
from .domain.services.handover_policy import HandoverPolicy
from .infrastructure import seed
from .infrastructure.integrations.mock_backend_systems import MockBackendSystems
from .infrastructure.messaging.whatsapp_cloud import WhatsAppCloudGateway
from .infrastructure.llm.openai_compatible_classifier import (OpenAICompatibleClassifier,
                                                              ResilientIntentClassifier)
from .infrastructure.llm.prompt_loader import PromptLoader
from .infrastructure.llm.rule_based_classifier import RuleBasedIntentClassifier
from .infrastructure.persistence import mongo as mongo_adapters
from .infrastructure.persistence.memory import (InMemoryAuditLog,
                                                InMemoryConversationRepository,
                                                InMemoryCustomerRepository,
                                                InMemorySessionRepository,
                                                InMemoryStudioConfigRepository)
from .infrastructure.persistence.redis_session import RedisSessionRepository
from .settings import Settings, get_settings

log = logging.getLogger("hub.container")


class Container:
    """Guarda as dependências resolvidas e expõe os casos de uso já montados."""

    sessions: SessionRepository
    conversations: ConversationRepository
    customers: CustomerRepository
    studio: StudioConfigRepository
    audit: AuditLog
    classifier: IntentClassifier
    backends: BackendSystems
    whatsapp: WhatsAppCloudGateway

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis_adapter: RedisSessionRepository | None = None

    # ------------------------------------------------------------ ciclo de vida
    async def startup(self) -> None:
        s = self.settings

        # -- sessão (curto prazo) -----------------------------------------
        redis_repo = await RedisSessionRepository.connect(s.redis_url, s.session_ttl_seconds)
        self._redis_adapter = redis_repo
        self.sessions = redis_repo or InMemorySessionRepository()

        # -- histórico (longo prazo) --------------------------------------
        db = await mongo_adapters.connect(s.mongo_url, s.mongo_db)
        if db is not None:
            self.conversations = mongo_adapters.MongoConversationRepository(db)
            self.customers = mongo_adapters.MongoCustomerRepository(db)
            self.studio = mongo_adapters.MongoStudioConfigRepository(db, seed.DEFAULT_STUDIO)
            self.audit = mongo_adapters.MongoAuditLog(db)
        else:
            self.conversations = InMemoryConversationRepository()
            self.customers = InMemoryCustomerRepository()
            self.studio = InMemoryStudioConfigRepository(seed.DEFAULT_STUDIO)
            self.audit = InMemoryAuditLog()

        # -- motor de intenção --------------------------------------------
        loader = PromptLoader()
        rules = RuleBasedIntentClassifier()
        if s.llm.enabled:
            config = await self.studio.get()
            primary = OpenAICompatibleClassifier(s.llm, loader, studio=config)
            self.classifier = ResilientIntentClassifier(primary, rules)
            log.info("Motor de intenção: %s (fallback: regras)", s.llm.model)
        else:
            self.classifier = rules
            log.info("Motor de intenção: regras (nenhuma LLM_API_KEY configurada)")

        # -- sistemas internos --------------------------------------------
        self.backends = MockBackendSystems()

        # -- canal WhatsApp (Cloud API) ------------------------------------
        self.whatsapp = WhatsAppCloudGateway(s.whatsapp)
        if s.whatsapp.can_send:
            log.info("Canal WhatsApp habilitado (Cloud API %s)", s.whatsapp.api_version)
        elif s.whatsapp.configured:
            log.info("Canal WhatsApp configurado, porém desligado "
                     "(defina WHATSAPP_ENABLED=true para ativar)")
        else:
            faltando = ", ".join(s.whatsapp.missing()) or "credenciais"
            log.info("Canal WhatsApp inativo — faltam: %s. O simulador continua disponível.",
                     faltando)

        await seed.populate(self.customers, self.conversations, self.studio)

    async def shutdown(self) -> None:
        if self._redis_adapter is not None:
            await self._redis_adapter.close()

    # ---------------------------------------------------------------- casos de uso
    @property
    def ingest_message(self) -> IngestMessageUseCase:
        return IngestMessageUseCase(
            sessions=self.sessions, conversations=self.conversations,
            customers=self.customers, studio=self.studio, classifier=self.classifier,
            backends=self.backends, audit=self.audit,
            handover_policy=HandoverPolicy(self.settings.handover_confidence_threshold),
        )

    @property
    def list_conversations(self) -> ListConversationsUseCase:
        return ListConversationsUseCase(self.conversations)

    @property
    def get_conversation(self) -> GetConversationUseCase:
        return GetConversationUseCase(self.conversations, self.customers, self.audit)

    @property
    def request_handover(self) -> RequestHandoverUseCase:
        return RequestHandoverUseCase(self.conversations, self.audit)

    @property
    def reply_as_agent(self) -> ReplyAsAgentUseCase:
        return ReplyAsAgentUseCase(self.conversations, self.audit)

    @property
    def customer_context(self) -> GetCustomerContextUseCase:
        return GetCustomerContextUseCase(self.customers, self.conversations,
                                         self.backends, self.audit)

    @property
    def dashboard_metrics(self) -> GetDashboardMetricsUseCase:
        return GetDashboardMetricsUseCase(self.conversations)

    @property
    def get_studio_config(self) -> GetStudioConfigUseCase:
        return GetStudioConfigUseCase(self.studio)

    @property
    def update_studio_config(self) -> UpdateStudioConfigUseCase:
        return UpdateStudioConfigUseCase(self.studio, self.audit)

    @property
    def update_channel_config(self) -> UpdateChannelConfigUseCase:
        return UpdateChannelConfigUseCase(self.studio, self.audit)


container = Container()


def get_container() -> Container:
    """Dependência do FastAPI. Testes injetam outro container por override."""
    return container
