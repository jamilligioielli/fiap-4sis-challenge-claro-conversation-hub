"""DTOs da camada HTTP.

Separados das entidades do domínio de propósito: o formato que a API expõe pode
mudar por razão de interface (paginação, rótulo em português, campo achatado para
o front) sem que o domínio seja arrastado junto — e vice-versa.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ...domain.value_objects import (Area, Author, Channel, ConversationStatus,
                                     Consent, Priority)


# ------------------------------------------------------------------ ingestão
class InboundMessageRequest(BaseModel):
    """Corpo que um adaptador de canal envia ao hub."""
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "text": "Olá, gostaria de alterar meu plano",
        "external_id": "5511987654321",
        "customer_id": None,
        "consent": {"granted": True, "scope": ["atendimento"]},
    }]})

    text: str = Field(min_length=1, max_length=4000,
                      description="Conteúdo da mensagem, como o cliente escreveu.")
    external_id: str | None = Field(
        default=None,
        description=("Identificador do cliente **neste canal**: telefone no WhatsApp, cookie "
                     "de sessão no site, device id no app. O hub resolve para o `customer_id`. "
                     "Nunca é usado como chave da memória."),
    )
    customer_id: str | None = Field(
        default=None,
        description="Informe quando o canal já autenticou o cliente. Dispensa o `external_id`.",
    )
    consent: Consent = Field(
        default_factory=Consent,
        description="Consentimento do cliente para este canal (LGPD). Sem ele, o hub recusa (403).",
    )


class IntentResponse(BaseModel):
    slug: str = Field(description="Identificador estável da intenção.")
    name: str = Field(description="Rótulo legível, como aparece no console.")
    confidence: float = Field(description="0.0 a 1.0. Abaixo do limiar, o hub prefere transferir.")
    confidence_label: str = Field(description="Alta, Média ou Baixa.")
    area: Area
    entities: dict = Field(default_factory=dict,
                           description="Entidades extraídas (plano, valor, protocolo).")
    engine: str = Field(description="`llm` ou `rules` — qual classificador respondeu.")
    reasoning: str | None = None


class HubReplyResponse(BaseModel):
    """Resposta do hub a uma mensagem de canal. Percorre os seis RFs."""
    conversation_id: str
    session_id: str
    customer_id: str
    channel: Channel
    reply: str = Field(description="Texto a devolver ao cliente, já com a persona aplicada.")
    intent: IntentResponse = Field(description="RF002.")
    flow: str = Field(description="RF004 — fluxo de negócio acionado.")
    persona_applied: str = Field(description="RF006 — configuração de persona usada.")
    context_recovered: bool = Field(
        description="RF003 — true quando o hub retomou uma conversa já existente.")
    context_note: str | None = Field(
        default=None,
        description="Preenchido quando houve troca de canal. É a evidência da continuidade.")
    handover_triggered: bool = Field(description="RF005.")
    handover_reason: str | None = None
    services_consulted: list[str] = Field(
        default_factory=list, description="Sistemas internos acionados nesta sessão.")
    turns: int


# ------------------------------------------------------------------ conversas
class ConversationListItem(BaseModel):
    """Item da fila do Inbox."""
    id: str
    customer_id: str
    customer_name: str
    channel: Channel = Field(description="Canal mais recente da conversa.")
    channels_used: list[Channel]
    status: ConversationStatus
    last_message: str
    timestamp: str = Field(description="Rótulo relativo pronto para exibição: 'Há 2 min'.")
    updated_at: datetime
    priority: Priority
    area: Area
    unread: bool
    intent: str | None = None
    confidence: float | None = None
    handover_requested: bool = False


class MessageResponse(BaseModel):
    id: str
    author: Author
    text: str
    channel: Channel | None = None
    timestamp: datetime
    intent: IntentResponse | None = None


class AIPanelResponse(BaseModel):
    """Painel lateral da Conversa Ativa."""
    intent: IntentResponse | None = None
    summary: dict[str, str] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)
    insights: list[dict] = Field(default_factory=list)
    handover: dict = Field(default_factory=dict)


class ConversationDetailResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    status: ConversationStatus
    area: Area
    priority: Priority
    channels_used: list[Channel]
    started_at: datetime
    messages: list[MessageResponse]
    ai: AIPanelResponse


class HandoverRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"reason": "Cliente solicitou atendimento humano", "agent": "Ana · CX"}]})

    reason: str = Field(default="Solicitado pelo console",
                        description="Registrado na trilha de auditoria.")
    agent: str | None = Field(default=None, description="Atendente que assume a conversa.")


class AgentMessageRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"text": "Oi Maria, sou a Ana. Já vi todo o histórico, pode deixar comigo."}]})

    text: str = Field(min_length=1, max_length=4000)
    channel: Channel | None = Field(
        default=None, description="Se omitido, responde pelo último canal usado pelo cliente.")


# ------------------------------------------------------------------- cliente
class PlanResponse(BaseModel):
    name: str
    price: float
    data_gb: int
    used_gb: float
    usage_percent: int
    line: str
    due_day: int
    status: str


class CustomerContextResponse(BaseModel):
    id: str
    name: str
    document_masked: str
    birth_date: str
    customer_since: str
    segment: str
    email: str
    phone: str
    preferred_channel: Channel
    plan: PlanResponse | None
    products: list[dict]
    timeline: list[dict]
    churn_risk: float
    churn_label: str
    churn_factors: list[dict]
    upgrade_options: list[dict]
    conversation_count: int
    channels_used: list[Channel]


# ----------------------------------------------------------------- dashboard
class KPIResponse(BaseModel):
    value: float
    trend: float
    unit: str = ""


class DashboardResponse(BaseModel):
    """Números crus. A formatação de exibição é responsabilidade da interface."""
    area: str
    conversations: KPIResponse
    resolution_rate: KPIResponse
    handover_rate: KPIResponse
    nps: KPIResponse
    week: list[dict]
    channels: list[dict]
    area_counts: dict[str, int]
    journey_breaks: list[dict]
    automation_opportunities: list[dict]
    alerts: list[dict]
    intents: list[dict]


# ------------------------------------------------------------------- health
class ComponentHealth(BaseModel):
    session_store: str = Field(description="`ok`, `down` ou `memory (fallback)`.")
    history_store: str
    intent_engine: str = Field(description="Classificador ativo e seu fallback.")
    backend_systems: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    components: ComponentHealth


class ErrorResponse(BaseModel):
    detail: str


# ------------------------------------------------------------------ WhatsApp
class WhatsAppStatusResponse(BaseModel):
    """Diagnóstico da integração. Nunca carrega token nem segredo."""
    enabled: bool = Field(description="WHATSAPP_ENABLED está ligado.")
    configured: bool = Field(description="Credenciais mínimas presentes.")
    can_send: bool = Field(description="Habilitado E configurado — pronto para enviar.")
    api_version: str
    phone_number_id: str = Field(description="Mascarado.")
    business_account_id: str = Field(description="Mascarado.")
    access_token: str = Field(description="`configurado` ou `ausente`.")
    verify_token: str = Field(description="`configurado` ou `ausente`.")
    signature_validation: bool = Field(
        description="Se falso, o webhook aceita qualquer payload — não use assim em produção.")
    default_recipient: str = Field(description="Mascarado.")
    webhook_url: str = Field(description="URL a cadastrar no painel da Meta.")
    missing: list[str] = Field(description="Variáveis de ambiente que faltam.")


class WhatsAppSendRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"to": "5511987654321", "text": "Teste de integração do Claro Conversation Hub."}]})

    text: str = Field(min_length=1, max_length=4000)
    to: str | None = Field(
        default=None,
        description="Telefone internacional, só dígitos. Omitido = WHATSAPP_DEFAULT_RECIPIENT.")
