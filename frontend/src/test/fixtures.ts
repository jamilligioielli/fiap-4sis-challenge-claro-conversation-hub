import type {
  ConversationDetail, ConversationHistory, ConversationListItem, CustomerContext, CustomerSummary,
  Dashboard, EligibleCustomer, Greeting, Health, HubReply, Intent, NpsComparison, NpsGroup,
  StudioConfig,
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
  awaiting_nps: false,
  conversation_closed: false,
  nps_score: null,
  superseded: false,
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
  nps_score: null,
  nps_category: null,
  closed_by: null,
  handover_requested_at: null,
  assigned_agent: null,
  waiting_seconds: null,
  attended_by: 'bot',
  sentiment: null,
  sentiment_score: null,
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
  sentiment: 'neutral',
  sentiment_score: 0.5,
  attended_by: 'bot',
  messages: [
    { id: 'm1', author: 'bot', text: 'Oi, Maria! 👋', channel: 'whatsapp',
      timestamp: '19:58', intent: null, source: 'template', sentiment: null },
    { id: 'm2', author: 'customer', text: 'Quero mais internet', channel: 'whatsapp',
      timestamp: '19:59', intent, source: null, sentiment: 'neutral' },
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

/** Atendimento encerrado com a pesquisa aberta, esperando a nota. */
export const npsReply: HubReply = {
  ...hubReply,
  reply: 'Antes de encerrar, Maria: de 0 a 10, o quanto você recomendaria a Claro '
       + 'para um amigo ou familiar? Pode responder só com o número.',
  flow: 'encerramento',
  awaiting_nps: true,
  conversation_closed: true,
  response_source: 'template',
  response_model: null,
};

/** Mensagem absorvida por outra mais recente do mesmo cliente. */
export const supersededReply: HubReply = {
  ...hubReply,
  reply: '',
  flow: 'agrupada',
  superseded: true,
};

/** Conversa já com o atendente: o assistente não responde mais. */
export const silentReply: HubReply = {
  ...hubReply,
  reply: '',
  flow: 'atendimento_humano',
  context_recovered: true,
  context_note: 'Mensagem entregue ao atendente responsável pelo caso',
  handover_triggered: true,
  handover_reason: 'Cliente solicitou falar com atendente',
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
    reply_delay_seconds: 30,
    nps_on_close: true,
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

// ------------------------------------------------ Sprint 4 — NPS comparativo
const emptyGroup: NpsGroup = {
  total: 0, average_score: null, nps: null, promoters: 0, passives: 0, detractors: 0,
  percentages: { promoters: 0, passives: 0, detractors: 0 }, surveys_sent: 0, unanswered: 0,
};

export const npsComparison: NpsComparison = {
  area: 'Todos',
  bot: {
    total: 10, average_score: 6.8, nps: -10, promoters: 3, passives: 3, detractors: 4,
    percentages: { promoters: 30, passives: 30, detractors: 40 }, surveys_sent: 12,
    unanswered: 2,
  },
  agent: {
    total: 5, average_score: 8.6, nps: 60, promoters: 3, passives: 2, detractors: 0,
    percentages: { promoters: 60, passives: 40, detractors: 0 }, surveys_sent: 5,
    unanswered: 0,
  },
  overall: {
    total: 15, average_score: 7.4, nps: 13.3, promoters: 6, passives: 5, detractors: 4,
    percentages: { promoters: 40, passives: 33.3, detractors: 26.7 }, surveys_sent: 17,
    unanswered: 2,
  },
  comparison: { score_difference: 1.8, nps_difference: 70, agent_better: true },
};

export const emptyNpsComparison: NpsComparison = {
  area: 'Todos', bot: emptyGroup, agent: emptyGroup, overall: emptyGroup,
  comparison: { score_difference: null, nps_difference: null, agent_better: null },
};

// ------------------------------------------------- Sprint 4 — histórico
export const conversationHistory: ConversationHistory = {
  customer_id: 'cus1',
  months: 6,
  items: [
    {
      id: 'conv1', date: '2026-08-30', started_at: '2026-08-30T19:58:00Z', closed_at: null,
      type: 'vendas', type_label: 'Vendas', intent: 'Alteração de Plano', area: 'Vendas',
      status: 'open', status_label: 'Em andamento', resolved: false, nps_score: null,
      nps_category: null, attended_by: 'bot', channels_used: ['whatsapp'], message_count: 2,
      sentiment: 'neutral', current: true,
    },
    {
      id: 'conv0', date: '2026-08-12', started_at: '2026-08-12T10:00:00Z',
      closed_at: '2026-08-12T10:20:00Z', type: 'suporte', type_label: 'Suporte',
      intent: 'Suporte Técnico', area: 'Suporte', status: 'resolved',
      status_label: 'Resolvida', resolved: true, nps_score: 9, nps_category: 'promotor',
      attended_by: 'agent', channels_used: ['app'], message_count: 8, sentiment: 'positive',
      current: false,
    },
    {
      id: 'conv-1', date: '2026-07-20', started_at: '2026-07-20T10:00:00Z',
      closed_at: '2026-07-20T10:30:00Z', type: 'financeiro', type_label: 'Financeiro',
      intent: 'Segunda Via de Fatura', area: 'Financeiro', status: 'unresolved',
      status_label: 'Encerrada com insatisfação', resolved: false, nps_score: 4,
      nps_category: 'detrator', attended_by: 'bot', channels_used: ['whatsapp'],
      message_count: 5, sentiment: 'negative', current: false,
    },
  ],
  insights: {
    total_conversations: 3, average_frequency_days: 20.5, most_common_type: 'suporte',
    most_common_type_label: 'Suporte', average_nps: 6.5, average_nps_category: 'detrator',
    resolution_rate: 50, closed_conversations: 2,
  },
};

export const emptyHistory: ConversationHistory = {
  customer_id: 'cus1', months: 6, items: [],
  insights: {
    total_conversations: 0, average_frequency_days: null, most_common_type: null,
    most_common_type_label: null, average_nps: null, average_nps_category: null,
    resolution_rate: null, closed_conversations: 0,
  },
};
