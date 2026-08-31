/**
 * Tipos espelhados da especificação OpenAPI do hub.
 *
 * Escritos à mão de propósito: são poucos e a clareza vale mais aqui do que a
 * geração automática. Se o contrato crescer, `openapi-typescript` gera isto a
 * partir de `/openapi.json`.
 */

export type Channel = 'whatsapp' | 'web' | 'app' | 'voice';
export type ConversationStatus = 'active' | 'waiting' | 'transferred' | 'pending';
export type Priority = 'high' | 'medium' | 'low';
export type Author = 'customer' | 'bot' | 'agent' | 'system';
export type Area =
  | 'Suporte' | 'Vendas' | 'Financeiro' | 'Marketing' | 'Retenção' | 'Técnico';

export type ResponseSource = 'generative' | 'template';

export interface Intent {
  slug: string;
  name: string;
  confidence: number;
  confidence_label: string;
  area: Area;
  entities: Record<string, string>;
  /** `llm` ou `rules` — qual classificador respondeu. */
  engine: string;
  reasoning: string | null;
}

/** Resposta do hub a uma mensagem de canal. Percorre os seis RFs. */
export interface HubReply {
  conversation_id: string;
  session_id: string;
  customer_id: string;
  channel: Channel;
  reply: string;
  intent: Intent;
  flow: string;
  persona_applied: string;
  context_recovered: boolean;
  context_note: string | null;
  persona_version: number;
  response_source: ResponseSource;
  response_model: string | null;
  awaiting_context_confirmation: boolean;
  handover_triggered: boolean;
  handover_reason: string | null;
  services_consulted: string[];
  turns: number;
}

/** Saudação de abertura, antes da primeira mensagem do cliente. */
export interface Greeting {
  conversation_id: string;
  session_id: string;
  customer_id: string;
  greeting: string;
  persona_applied: string;
  persona_version: number;
  response_source: ResponseSource;
  response_model: string | null;
  resumed: boolean;
}

/** Cliente na lista de personas do simulador. */
export interface CustomerSummary {
  id: string;
  name: string;
  segment: string;
  persona_summary: string;
  preferred_channel: Channel;
  plan_name: string | null;
  plan_usage_percent: number | null;
  churn_label: string;
  marketing_opt_in: boolean;
  conversation_count: number;
  open_conversation_id: string | null;
}

export interface EligibilityReason {
  code: string;
  description: string;
  weight: number;
}

export interface OutreachBlock {
  code: string;
  description: string;
}

export interface Offer {
  id: string;
  title: string;
  pitch: string;
  category: string;
  plan_name: string | null;
  price: number | null;
  saving_hint: string;
}

export interface EligibleCustomer {
  customer_id: string;
  customer_name: string;
  segment: string;
  score: number;
  reasons: EligibilityReason[];
  blocks: OutreachBlock[];
  suggested_offer: Offer | null;
  window_open: boolean;
  window_hours_remaining: number;
  marketing_opt_in: boolean;
  can_contact: boolean;
  requires_template: boolean;
}

export interface OutreachResult {
  conversation_id: string;
  customer_id: string;
  message: string;
  channel: string;
  template_category: string;
  used_template: boolean;
  response_source: ResponseSource;
}

export interface ChannelPreview {
  channel_id: string;
  channel_name: string;
  formality_label: string;
  use_emoji: boolean;
  max_length: number;
  rendered: string;
  length: number;
}

export interface PersonaPreview {
  persona_name: string;
  persona_version: number;
  original: string;
  previews: ChannelPreview[];
}

export interface ConversationListItem {
  id: string;
  customer_id: string;
  customer_name: string;
  channel: Channel;
  channels_used: Channel[];
  status: ConversationStatus;
  last_message: string;
  timestamp: string;
  updated_at: string;
  priority: Priority;
  area: Area;
  unread: boolean;
  intent: string | null;
  confidence: number | null;
  handover_requested: boolean;
  initiated_by_company: boolean;
  message_count: number;
  started_at: string;
}

export interface Message {
  id: string;
  author: Author;
  text: string;
  channel: Channel | null;
  timestamp: string;
  intent: Intent | null;
  source: ResponseSource | null;
}

export interface AIPanel {
  intent: Intent | null;
  summary: Record<string, string>;
  suggestions: string[];
  insights: { text: string; tone: string }[];
  handover: {
    requested: boolean;
    reason: string | null;
    assigned_agent: string | null;
    services_consulted: string[];
    transcript_size: number;
  };
}

export interface ConversationDetail {
  id: string;
  customer_id: string;
  customer_name: string;
  status: ConversationStatus;
  area: Area;
  priority: Priority;
  channels_used: Channel[];
  started_at: string;
  messages: Message[];
  ai: AIPanel;
}

export interface Plan {
  name: string;
  price: number;
  data_gb: number;
  used_gb: number;
  usage_percent: number;
  line: string;
  due_day: number;
  status: string;
}

export interface CustomerContext {
  id: string;
  name: string;
  document_masked: string;
  birth_date: string;
  customer_since: string;
  segment: string;
  email: string;
  phone: string;
  preferred_channel: Channel;
  persona_summary: string;
  marketing_opt_in: boolean;
  plan: Plan | null;
  products: { name: string; status: string; description: string }[];
  timeline: { date: string; event: string; type: string }[];
  churn_risk: number;
  churn_label: string;
  churn_factors: { text: string; positive: boolean }[];
  upgrade_options: { name: string; price: number; data_gb: number; status: string }[];
  conversation_count: number;
  channels_used: Channel[];
}

export interface KPI {
  value: number;
  trend: number;
  unit: string;
}

export interface Dashboard {
  area: string;
  has_data: boolean;
  conversations: KPI;
  resolution_rate: KPI;
  handover_rate: KPI;
  nps: KPI;
  week: { day: string; conversations: number }[];
  channels: { name: string; value: number; color: string }[];
  area_counts: Record<string, number>;
  journey_breaks: { journey: string; break: string; impact: string; occurrences: number }[];
  automation_opportunities: { area: string; potential: number; estimated_savings_brl: number }[];
  alerts: { severity: string; title: string; description: string }[];
  intents: { name: string; count: number }[];
}

// ------------------------------------------------------------- Design Studio
export interface VoiceConfig {
  speechRate: number;
  voiceGender: 'feminino' | 'masculino';
  vocabularyLevel: number;
  captureMode: 'dtmf' | 'voice' | 'hybrid';
  menuPattern: 'option-key' | 'key-option';
  maxMenuOptions: number;
  autoRepeatTimeout: number;
  maxAttempts: number;
  silenceTimeout: number;
  transferTriggers: string[];
  queueMessage: string;
  scriptOpening: string;
  scriptMenu: string;
  scriptFarewell: string;
  pronunciationGlossary: { term: string; pronunciation: string }[];
}

export interface ChannelPresentation {
  color: string;
  bgColor: string;
  iconColor: string;
}

export interface ChannelConfig {
  id: string;
  name: string;
  formalityLevel: number;
  greeting: string;
  maxLength: number;
  useEmoji: boolean;
  guidelines: string[];
  sampleMessage: string;
  presentation: ChannelPresentation;
  voiceConfig: VoiceConfig | null;
}

export interface StudioConfig {
  persona: { name: string; description: string; traits: string[] };
  intents: { slug: string; name: string; confidence: string; examples: string }[];
  guardrails: { rule: string; category: string }[];
  channels: ChannelConfig[];
  version: number;
  updated_at: string;
}

export interface Health {
  status: string;
  version: string;
  environment: string;
  components: {
    session_store: string;
    history_store: string;
    intent_engine: string;
    response_generator: string;
    generative_ai: boolean;
    backend_systems: string[];
  };
}

// ----------------------------------------------------------------- WhatsApp
export interface WhatsAppStatus {
  enabled: boolean;
  configured: boolean;
  can_send: boolean;
  api_version: string;
  phone_number_id: string;
  business_account_id: string;
  access_token: string;
  verify_token: string;
  signature_validation: boolean;
  default_recipient: string;
  webhook_url: string;
  missing: string[];
}
