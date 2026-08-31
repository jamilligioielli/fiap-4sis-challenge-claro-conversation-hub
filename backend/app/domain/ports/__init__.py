"""Portas do domínio (Ports & Adapters).

Interfaces que o domínio e os casos de uso conhecem. Toda implementação concreta
vive em `infrastructure/` e depende destas abstrações, nunca o contrário.
"""
from __future__ import annotations

from .audit_log import AuditLog
from .backend_systems import BackendSystems
from .conversation_repository import ConversationRepository
from .customer_repository import CustomerRepository
from .intent_classifier import IntentClassifier
from .outbound_gateway import OutboundGateway
from .response_generator import (GeneratedResponse, GenerationRequest, ResponseGenerator)
from .session_repository import SessionRepository
from .studio_config_repository import StudioConfigRepository

__all__ = [
    "AuditLog", "BackendSystems", "ConversationRepository", "CustomerRepository",
    "GeneratedResponse", "GenerationRequest", "IntentClassifier", "OutboundGateway",
    "ResponseGenerator", "SessionRepository", "StudioConfigRepository",
]
