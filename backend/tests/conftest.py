"""Ambiente dos testes.

O container é montado com adaptadores em memória, sem Redis e sem MongoDB: a
suíte precisa rodar em qualquer máquina e no CI, e a arquitetura hexagonal existe
justamente para tornar isso possível sem mudar uma linha de caso de uso.

Cada teste recebe um container novo. Estado que sobrevive entre testes produz
falha intermitente — o tipo de bug que custa mais caro do que o teste economiza.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from app.container import Container, get_container
from app.domain.value_objects.channel import Channel
from app.infrastructure import seed
from app.infrastructure.integrations.mock_backend_systems import MockBackendSystems
from app.infrastructure.llm.rule_based_classifier import RuleBasedIntentClassifier
from app.infrastructure.llm.template_response_generator import TemplateResponseGenerator
from app.infrastructure.messaging.whatsapp_cloud import WhatsAppCloudGateway
from app.infrastructure.persistence.memory import (InMemoryAuditLog,
                                                   InMemoryConversationRepository,
                                                   InMemoryCustomerRepository,
                                                   InMemorySessionRepository,
                                                   InMemoryStudioConfigRepository)
from app.main import create_app
from app.settings import Settings


async def build_container() -> Container:
    """Container equivalente ao de produção, porém todo em memória."""
    container = Container(Settings())
    container.sessions = InMemorySessionRepository()
    container.conversations = InMemoryConversationRepository()
    container.customers = InMemoryCustomerRepository()
    container.studio = InMemoryStudioConfigRepository(seed.DEFAULT_STUDIO)
    container.audit = InMemoryAuditLog()
    container.classifier = RuleBasedIntentClassifier()
    container.generator = TemplateResponseGenerator()
    container.backends = MockBackendSystems()
    container.whatsapp = WhatsAppCloudGateway(container.settings.whatsapp)
    container.generative_ai = False
    await seed.populate(container.customers, container.conversations, container.studio)
    return container


@pytest.fixture
async def container() -> Container:
    return await build_container()


@pytest.fixture
def client(container: Container):
    """Cliente HTTP com o container de teste no lugar do global.

    O `lifespan` é substituído pela sobrescrita da dependência: subir Redis e
    MongoDB de verdade para testar um roteador seria testar a infraestrutura, não
    o contrato.
    """
    app = create_app()
    app.router.lifespan_context = _noop_lifespan
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def maria(container: Container):
    """A persona usada na maioria dos testes: franquia quase estourada e opt-in."""
    customers = await container.customers.all()
    return next(c for c in customers if c.name.startswith("Maria"))


@pytest.fixture
async def felipe(container: Container):
    """A persona que não pode ser abordada: sem opt-in e com risco de saída."""
    customers = await container.customers.all()
    return next(c for c in customers if c.name.startswith("Felipe"))

@asynccontextmanager
async def _noop_lifespan(_app):
    yield


def send(client: TestClient, channel: Channel | str, text: str,
         customer_id: str | None = None, external_id: str | None = None):
    """Atalho para o endpoint de ingestão, que quase todo teste usa."""
    channel_value = channel.value if isinstance(channel, Channel) else channel
    body: dict = {"text": text}
    if customer_id:
        body["customer_id"] = customer_id
    if external_id:
        body["external_id"] = external_id
    return client.post(f"/api/v1/channels/{channel_value}/messages", json=body)
