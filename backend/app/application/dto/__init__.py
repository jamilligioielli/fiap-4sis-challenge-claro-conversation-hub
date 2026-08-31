"""Objetos de transporte entre a camada de interface e os casos de uso."""
from __future__ import annotations

from .conversation_detail import ConversationDetail
from .customer_context import CustomerContext
from .dashboard_metrics import DashboardMetrics
from .ingest_command import IngestCommand
from .ingest_result import IngestResult
from .kpi import KPI
from .list_conversations_query import ListConversationsQuery
from .outreach_command import SendOutreachCommand
from .preview_command import PreviewPersonaCommand

__all__ = [
    "ConversationDetail", "CustomerContext", "DashboardMetrics", "IngestCommand",
    "IngestResult", "KPI", "ListConversationsQuery", "PreviewPersonaCommand",
    "SendOutreachCommand",
]
