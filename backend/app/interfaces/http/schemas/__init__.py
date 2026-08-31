"""DTOs da camada HTTP.

Separados das entidades do domínio de propósito: o formato que a API expõe pode
mudar por razão de interface sem arrastar o domínio junto — e vice-versa.
Cada classe vive no seu próprio arquivo; este módulo apenas reexporta.
"""
from __future__ import annotations

from .agent_message_request import AgentMessageRequest
from .ai_panel_response import AIPanelResponse
from .component_health import ComponentHealth
from .conversation_detail_response import ConversationDetailResponse
from .conversation_list_item import ConversationListItem
from .customer_context_response import CustomerContextResponse
from .customer_summary_response import CustomerSummaryResponse
from .dashboard_response import DashboardResponse
from .eligible_customer_response import EligibleCustomerResponse
from .error_response import ErrorResponse
from .greeting_response import GreetingResponse
from .handover_request import HandoverRequest
from .health_response import HealthResponse
from .hub_reply_response import HubReplyResponse
from .inbound_message_request import InboundMessageRequest
from .intent_response import IntentResponse
from .kpi_response import KPIResponse
from .message_response import MessageResponse
from .outreach_result_response import OutreachResultResponse
from .persona_preview_request import PersonaPreviewRequest
from .persona_preview_response import ChannelPreview, PersonaPreviewResponse
from .plan_response import PlanResponse
from .send_outreach_request import SendOutreachRequest
from .start_conversation_request import StartConversationRequest
from .whatsapp_send_request import WhatsAppSendRequest
from .whatsapp_status_response import WhatsAppStatusResponse

__all__ = [
    "AgentMessageRequest", "AIPanelResponse", "ChannelPreview", "ComponentHealth",
    "ConversationDetailResponse", "ConversationListItem", "CustomerContextResponse",
    "CustomerSummaryResponse", "DashboardResponse", "EligibleCustomerResponse",
    "ErrorResponse", "GreetingResponse", "HandoverRequest", "HealthResponse",
    "HubReplyResponse", "InboundMessageRequest", "IntentResponse", "KPIResponse",
    "MessageResponse", "OutreachResultResponse", "PersonaPreviewRequest",
    "PersonaPreviewResponse", "PlanResponse", "SendOutreachRequest",
    "StartConversationRequest", "WhatsAppSendRequest", "WhatsAppStatusResponse",
]
