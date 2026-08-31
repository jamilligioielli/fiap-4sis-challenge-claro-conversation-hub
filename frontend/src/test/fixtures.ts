import type {
  ConversationDetail, ConversationListItem, CustomerContext, CustomerSummary,
  Dashboard, EligibleCustomer, Greeting, Health, HubReply, Intent, StudioConfig,
} from '../app/api/types';

/**
 * Dados de teste.
 *
 * Espelham a forma que a API devolve de verdade — conferida contra a
 * especificação OpenAPI. Um fixture que diverge do contrato transforma o teste
 * em decoração: passa verde enquanto a tela quebra.
 */

export const intent: Intent = {
  slug: 'alteracao_plano',
  name: 'Alteração de Plano',
  confidence: 0.88,
  confidence_label: 'Alta',
  area: 'Vendas',
  entities: { plano: 'Flex 50GB' },
  engine: 'rules',
  reasoning: null,
};

export const greeting: Greeting = {
  conversation_id: 'conv1',
  session_id: 'ses1',
  customer_id: 'cus1',
  greeting: 'Oi, Maria! 👋 Sou a Clara, assistente virtual da Claro. Como posso te ajudar?',
  persona_applied: 'Clara · WhatsApp · informal, com emojis',
  persona_version: 3,
  response_source: 'template',
  response_model: null,
  resumed: false,
};

export const hubReply: HubReply = {
  conversation_id: 'conv1',
  session_id: 'ses1',
  customer_id: 'cus1',
  channel: 'whatsapp',
  reply: 'Claro! Vi que você usa 92% da franquia. Posso te mostrar o Flex 50GB?',
  intent,
  flow: 'vendas.upgrade',
  persona_applied: 'Clara · WhatsApp · informal, com emojis',
  context_recovered: false,
  context_note: null,
  persona_version: 3,
  response_source: 'generative',
  response_model: 'llama-3.3-70b-versatile',
  awaiting_context_confirmation: false,
  handover_triggered: false,
  handover_reason: null,
  services_consulted: ['crm', 'catalogo'],
  turns: 1,
};

export const awaitingReply: HubReply = {
  ...hubReply,
  channel: 'app',
  reply: 'Vi que você estava tratando sobre alteração de plano pelo WhatsApp. '
       + 'Quer continuar nesse assunto por aqui, ou prefere tratar de outra coisa?',
  context_recovered: true,
  context_note: 'Conversa retomada do WhatsApp.',
  awaiting_context_confirmation: true,
};

export const customerSummary: CustomerSummary = {
  id: 'cus1',
  name: 'Maria Silva Santos',
  segment: 'VIP',
  persona_summary: 'Usa quase toda a franquia todo mês e já pesquisou planos maiores.',
  preferred_channel: 'whatsapp',
  plan_name: 'Claro Flex 30GB',
  plan_usage_percent: 92,
  churn_label: 'Baixo',
  marketing_opt_in: true,
  conversation_count: 2,
  open_conversation_id: 'conv1',
};

export const customerWithoutOptIn: CustomerSummary = {
  ...customerSummary,
  id: 'cus2',
  name: 'Felipe Barros',
  segment: 'Padrão',
  persona_summary: 'Reclamou de sinal duas vezes no último mês.',
  preferred_channel: 'app',
  plan_name: 'Claro Controle 12GB',
  plan_usage_percent: 40,
  churn_label: 'Alto',
  marketing_opt_in: false,
  conversation_count: 0,
  open_conversation_id: null,
};

export const customerContext: CustomerContext = {
  id: 'cus1',
  name: 'Maria Silva Santos',
  document_masked: '***.456.789-**',
  birth_date: '12/03/1988',
  customer_since: '2019',
  segment: 'VIP',
  email: 'maria@exemplo.com',
  phone: '+55 11 99999-0001',
  preferred_channel: 'whatsapp',
  persona_summary: 'Usa quase toda a franquia todo mês.',
  marketing_opt_in: true,
  plan: {
    name: 'Claro Flex 30GB', price: 79.9, data_gb: 30, used_gb: 27.6,
    usage_percent: 92, line: '+55 11 99999-0001', due_day: 10, status: 'ativo',
  },
  products: [],
  timeline: [],
  churn_risk: 0.12,
  churn_label: 'Baixo',
  churn_factors: [],
  upgrade_options: [],
  conversation_count: 2,
  channels_used: ['whatsapp', 'app'],
};

export const conversationItem: ConversationListItem = {
  id: 'conv1',
  customer_id: 'cus1',
  customer_name: 'Maria Silva Santos',
  channel: 'whatsapp',
  channels_used: ['whatsapp'],
  status: 'active',
  last_message: 'Posso te mostrar o Flex 50GB?',
  timestamp: 'há 2 min',
  updated_at: '2026-08-30T20:00:00Z',
  priority: 'medium',
  area: 'Vendas',
  unread: false,
  intent: 'Alteração de Plano',
  confidence: 0.88,
  handover_requested: false,
  initiated_by_company: false,
  message_count: 4,
  started_at: '2026-08-30T19:58:00Z',
};

export const conversationDetail: ConversationDetail = {
  id: 'conv1',
  customer_id: 'cus1',
  customer_name: 'Maria Silva Santos',
  status: 'active',
  area: 'Vendas',
  priority: 'medium',
  channels_used: ['whatsapp'],
  started_at: '2026-08-30T19:58:00Z',
  messages: [
    { id: 'm1', author: 'bot', text: 'Oi, Maria! 👋', channel: 'whatsapp',
      timestamp: '19:58', intent: null, source: 'template' },
    { id: 'm2', author: 'customer', text: 'Quero mais internet', channel: 'whatsapp',
      timestamp: '19:59', intent, source: null },
  ],
  ai: {
    intent,
    summary: {},
    suggestions: [],
    insights: [],
    handover: { requested: false, reason: null, assigned_agent: null,
                services_consulted: [], transcript_size: 2 },
  },
};

export const emptyDashboard: Dashboard = {
  area: 'Todos',
  has_data: false,
  conversations: { value: 0, trend: 0, unit: '' },
  resolution_rate: { value: 0, trend: 0, unit: '%' },
  handover_rate: { value: 0, trend: 0, unit: '%' },
  nps: { value: 0, trend: 0, unit: '' },
  week: [],
  channels: [],
  area_counts: {},
  journey_breaks: [],
  automation_opportunities: [],
  alerts: [],
  intents: [],
};

export const filledDashboard: Dashboard = {
  ...emptyDashboard,
  has_data: true,
  conversations: { value: 12, trend: 4, unit: '' },
  resolution_rate: { value: 75, trend: 2, unit: '%' },
  handover_rate: { value: 8.3, trend: -1, unit: '%' },
  nps: { value: 64, trend: 3, unit: '' },
  week: [{ day: 'Seg', conversations: 12 }],
  channels: [{ name: 'WhatsApp', value: 12, color: '#25D366' }],
  area_counts: { Vendas: 12 },
  intents: [{ name: 'Alteração de Plano', count: 12 }],
};

export const eligibleContactable: EligibleCustomer = {
  customer_id: 'cus1',
  customer_name: 'Maria Silva Santos',
  segment: 'VIP',
  score: 1.05,
  reasons: [
    { code: 'franquia_alta', description: 'Usa 92% da franquia todo mês', weight: 0.5 },
    { code: 'cliente_antigo', description: 'Cliente há mais de 5 anos', weight: 0.25 },
  ],
  blocks: [],
  suggested_offer: {
    id: 'offer-flex-50', title: 'Claro Flex 50GB',
    pitch: 'Mais 20GB pelo mesmo perfil de uso.', category: 'marketing',
    plan_name: 'Claro Flex 50GB', price: 99.9, saving_hint: 'Sem franquia estourada.',
  },
  window_open: true,
  window_hours_remaining: 18,
  marketing_opt_in: true,
  can_contact: true,
  requires_template: false,
};

export const eligibleBlocked: EligibleCustomer = {
  ...eligibleContactable,
  customer_id: 'cus2',
  customer_name: 'Felipe Barros',
  segment: 'Padrão',
  score: 0.4,
  reasons: [
    { code: 'plano_antigo', description: 'Está num plano descontinuado', weight: 0.4 },
  ],
  blocks: [
    { code: 'sem_opt_in', description: 'Cliente não autorizou receber ofertas' },
    { code: 'risco_churn', description: 'Risco de saída alto — abordagem comercial pode irritar' },
  ],
  window_open: false,
  window_hours_remaining: 0,
  marketing_opt_in: false,
  can_contact: false,
  requires_template: true,
};

export const health: Health = {
  status: 'ok',
  version: '1.0.0',
  environment: 'development',
  components: {
    session_store: 'redis',
    history_store: 'mongodb',
    intent_engine: 'rules',
    response_generator: 'modelo de texto',
    generative_ai: false,
    backend_systems: ['crm', 'catalogo'],
  },
};

export const studioConfig: StudioConfig = {
  persona: { name: 'Clara', description: 'Assistente da Claro', traits: ['clara', 'direta'] },
  intents: [],
  guardrails: [],
  channels: [],
  version: 3,
  updated_at: '2026-08-30T19:00:00Z',
};
