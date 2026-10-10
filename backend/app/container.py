"""Composition root.

Único lugar do sistema onde implementações concretas são escolhidas e ligadas às
portas. Todo o resto do código depende de abstrações; a decisão de "cache ou
memória", "modelo de linguagem ou regras" é tomada aqui e em nenhum outro lugar.

Trocar de infraestrutura é editar este arquivo — nenhum caso de uso muda.
"""
from __future__ import annotations

import logging

from .application.use_cases.console import (GetConversationUseCase, ListConversationsUseCase,
                                            ReplyAsAgentUseCase, RequestHandoverUseCase)
from .application.use_cases.close_conversation import CloseConversationUseCase
from .application.use_cases.conversation_history import GetConversationHistoryUseCase
from .application.use_cases.customer_context import GetCustomerContextUseCase
from .application.use_cases.dashboard import (GetDashboardMetricsUseCase,
                                              GetNpsComparisonUseCase)
from .application.use_cases.ingest_message import IngestMessageUseCase
from .application.use_cases.list_customers import ListCustomersUseCase
from .application.use_cases.outreach import (ListEligibleCustomersUseCase, SendOutreachUseCase)
from .application.use_cases.preview_persona import PreviewPersonaUseCase
from .application.use_cases.start_conversation import StartConversationUseCase
from .application.use_cases.studio_config import (GetStudioConfigUseCase,
                                                  UpdateChannelConfigUseCase,
                                                  UpdateStudioConfigUseCase)
from .domain.ports.audit_log import AuditLog
from .domain.ports.backend_systems import BackendSystems
from .domain.ports.conversation_repository import ConversationRepository
from .domain.ports.customer_repository import CustomerRepository
from .domain.ports.intent_classifier import IntentClassifier
from .domain.ports.response_generator import ResponseGenerator
from .domain.ports.session_repository import SessionRepository
from .domain.ports.studio_config_repository import StudioConfigRepository
from .domain.services.handover_policy import HandoverPolicy
from .infrastructure import demo_seed, seed
from .infrastructure.buffering.message_debouncer import MessageDebouncer
from .infrastructure.integrations.mock_backend_systems import MockBackendSystems
from .infrastructure.llm.llm_client import LLMClient
from .infrastructure.llm.llm_intent_classifier import LLMIntentClassifier
from .infrastructure.llm.llm_response_generator import LLMResponseGenerator
from .infrastructure.llm.prompt_loader import PromptLoader
from .infrastructure.llm.resilient_intent_classifier import ResilientIntentClassifier
from .infrastructure.llm.resilient_response_generator import ResilientResponseGenerator
from .infrastructure.llm.rule_based_classifier import RuleBasedIntentClassifier
from .infrastructure.llm.template_response_generator import TemplateResponseGenerator
from .infrastructure.messaging.whatsapp_cloud import WhatsAppCloudGateway
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
    sessions: SessionRepository
    conversations: ConversationRepository
    customers: CustomerRepository
    studio: StudioConfigRepository
    audit: AuditLog
    classifier: IntentClassifier
    generator: ResponseGenerator
    backends: BackendSystems
    whatsapp: WhatsAppCloudGateway

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis_adapter: RedisSessionRepository | None = None
        self.generative_ai = False
        self.debouncer = MessageDebouncer(
            self.settings.conversation.reply_delay_seconds)

    # ------------------------------------------------------------ ciclo de vida
    async def startup(self) -> None:
        s = self.settings

        redis_repo = await RedisSessionRepository.connect(s.redis_url, s.session_ttl_seconds)
        self._redis_adapter = redis_repo
        self.sessions = redis_repo or InMemorySessionRepository()

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

        await seed.populate(self.customers, self.conversations, self.studio)
        if s.demo_seed:
            await demo_seed.populate_demo(self.customers, self.conversations)
        self._wire_language_model(s)
        self.backends = MockBackendSystems()
        self.whatsapp = WhatsAppCloudGateway(s.whatsapp)
        self._log_whatsapp(s)

    def _wire_language_model(self, s: Settings) -> None:
        loader = PromptLoader()
        rules = RuleBasedIntentClassifier()
        templates = TemplateResponseGenerator()

        if not s.llm.enabled:
            self.classifier = rules
            self.generator = templates
            self.generative_ai = False
            log.info("Sem chave de modelo de linguagem: classificação por regras e "
                     "respostas por modelo de texto.")
            return

        client = LLMClient(s.llm)
        self.classifier = ResilientIntentClassifier(
            LLMIntentClassifier(client, loader, studio=seed.DEFAULT_STUDIO), rules)
        self.generator = ResilientResponseGenerator(
            LLMResponseGenerator(client, loader), templates)
        self.generative_ai = True
        log.info("IA generativa ativa: %s redigindo as respostas.", s.llm.model)

    @staticmethod
    def _log_whatsapp(s: Settings) -> None:
        if s.whatsapp.can_send:
            log.info("Canal WhatsApp habilitado (Cloud API %s)", s.whatsapp.api_version)
        elif s.whatsapp.configured:
            log.info("Canal WhatsApp configurado, porém desligado.")
        else:
            log.info("Canal WhatsApp inativo — o simulador continua disponível.")

    async def shutdown(self) -> None:
        if self._redis_adapter is not None:
            await self._redis_adapter.close()

    # ---------------------------------------------------------- casos de uso
    @property
    def ingest_message(self) -> IngestMessageUseCase:
        return IngestMessageUseCase(
            sessions=self.sessions, conversations=self.conversations,
            customers=self.customers, studio=self.studio, classifier=self.classifier,
            generator=self.generator, backends=self.backends, audit=self.audit,
            handover_policy=HandoverPolicy(self.settings.handover_confidence_threshold),
        )

    @property
    def start_conversation(self) -> StartConversationUseCase:
        return StartConversationUseCase(
            self.sessions, self.conversations, self.customers, self.studio, self.generator)

    @property
    def list_customers(self) -> ListCustomersUseCase:
        return ListCustomersUseCase(self.customers, self.conversations)

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
    def close_conversation(self) -> CloseConversationUseCase:
        return CloseConversationUseCase(
            self.conversations, self.sessions, self.customers, self.studio, self.audit)

    @property
    def customer_context(self) -> GetCustomerContextUseCase:
        return GetCustomerContextUseCase(self.customers, self.conversations,
                                         self.backends, self.audit)

    @property
    def conversation_history(self) -> GetConversationHistoryUseCase:
        return GetConversationHistoryUseCase(self.conversations, self.customers, self.audit)

    @property
    def dashboard_metrics(self) -> GetDashboardMetricsUseCase:
        return GetDashboardMetricsUseCase(self.conversations)

    @property
    def nps_comparison(self) -> GetNpsComparisonUseCase:
        return GetNpsComparisonUseCase(self.conversations)

    @property
    def get_studio_config(self) -> GetStudioConfigUseCase:
        return GetStudioConfigUseCase(self.studio)

    @property
    def update_studio_config(self) -> UpdateStudioConfigUseCase:
        return UpdateStudioConfigUseCase(self.studio, self.audit)

    @property
    def update_channel_config(self) -> UpdateChannelConfigUseCase:
        return UpdateChannelConfigUseCase(self.studio, self.audit)

    async def list_conversations_for_customer(self, customer_id: str):
        """Histórico de um cliente, do mais recente para o mais antigo."""
        return await self.conversations.list(customer_id=customer_id)

    @property
    def preview_persona(self) -> PreviewPersonaUseCase:
        return PreviewPersonaUseCase(self.studio, self.customers)

    @property
    def list_eligible_customers(self) -> ListEligibleCustomersUseCase:
        return ListEligibleCustomersUseCase(self.customers)

    @property
    def send_outreach(self) -> SendOutreachUseCase:
        return SendOutreachUseCase(
            self.customers, self.conversations, self.sessions, self.studio,
            self.generator, self.audit)


container = Container()


def get_container() -> Container:
    """Dependência do FastAPI. Testes injetam outro container por sobrescrita."""
    return container
