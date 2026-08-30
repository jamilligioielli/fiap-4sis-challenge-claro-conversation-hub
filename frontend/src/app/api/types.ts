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
  handover_triggered: boolean;
  handover_reason: string | null;
  services_consulted: string[];
  turns: number;
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
}

export interface Message {
  id: string;
  author: Author;
  text: string;
  channel: Channel | null;
  timestamp: string;
  intent: Intent | null;
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
