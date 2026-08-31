/**
 * Cliente HTTP do Claro Conversation Hub.
 *
 * Único ponto do front-end que conhece a URL da API. As telas falam com os
 * hooks; os hooks falam com este módulo. Trocar o transporte não vaza para
 * dentro dos componentes.
 */
import type {
  Channel, ConversationDetail, ConversationListItem, CustomerContext,
  CustomerSummary, Dashboard, EligibleCustomer, Greeting, Health, HubReply,
  Message, OutreachResult, PersonaPreview, StudioConfig, WhatsAppStatus,
} from './types';

/** Em desenvolvimento o Vite faz proxy de /api e /health para o back-end. */
const BASE_URL = (import.meta as any).env?.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    // Distinguir "API fora do ar" de "API respondeu erro" importa: a primeira
    // é problema de ambiente, a segunda é problema de uso.
    throw new ApiError(0, 'Não foi possível alcançar a API do hub.');
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new ApiError(response.status, detail?.detail ?? response.statusText);
  }

  return response.status === 204 ? (undefined as T) : response.json();
}

function query(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export const api = {
  // -- Ingestão de canais (o que os canais chamam) ------------------------
  sendAsCustomer(channel: Channel, body: {
    text: string; external_id?: string; customer_id?: string;
    consent?: { granted: boolean; scope: string[] };
  }): Promise<HubReply> {
    return request(`/api/v1/channels/${channel}/messages`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  listChannels(): Promise<unknown[]> {
    return request('/api/v1/channels');
  },

  /** Abre a conversa e recebe a saudação do assistente, antes da primeira mensagem. */
  startConversation(customerId: string, channel: Channel): Promise<Greeting> {
    return request('/api/v1/channels/conversations', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId, channel }),
    });
  },

  // -- Canal WhatsApp (usado apenas pela documentação e pela operação) -----
  getWhatsAppStatus(): Promise<WhatsAppStatus> {
    return request('/api/v1/channels/whatsapp/status');
  },

  // -- Console ------------------------------------------------------------
  listConversations(filters: {
    area?: string; channel?: string; status?: string; search?: string;
  } = {}): Promise<ConversationListItem[]> {
    return request(`/api/v1/conversations${query(filters)}`);
  },

  getConversation(id: string): Promise<ConversationDetail> {
    return request(`/api/v1/conversations/${id}`);
  },

  requestHandover(id: string, reason: string, agent?: string): Promise<ConversationListItem> {
    return request(`/api/v1/conversations/${id}/handover`, {
      method: 'POST',
      body: JSON.stringify({ reason, agent }),
    });
  },

  replyAsAgent(id: string, text: string, channel?: Channel): Promise<Message> {
    return request(`/api/v1/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text, channel }),
    });
  },

  listCustomers(): Promise<CustomerSummary[]> {
    return request('/api/v1/customers');
  },

  getCustomerContext(customerId: string): Promise<CustomerContext> {
    return request(`/api/v1/customers/${customerId}/context`);
  },

  listCustomerConversations(customerId: string): Promise<ConversationListItem[]> {
    return request(`/api/v1/customers/${customerId}/conversations`);
  },

  getDashboard(area?: string): Promise<Dashboard> {
    return request(`/api/v1/dashboard${query({ area })}`);
  },

  // -- Design Studio ------------------------------------------------------
  getStudioConfig(): Promise<StudioConfig> {
    return request('/api/v1/studio/config');
  },

  saveStudioConfig(config: StudioConfig): Promise<StudioConfig> {
    return request('/api/v1/studio/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  },

  saveChannelConfig(channelId: string, patch: Record<string, unknown>): Promise<StudioConfig> {
    return request(`/api/v1/studio/channels/${channelId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
  },

  /** Mostra como a mesma frase sai em cada canal com a configuração vigente. */
  previewPersona(message: string, channels?: string[],
                 customerId?: string): Promise<PersonaPreview> {
    return request('/api/v1/studio/preview', {
      method: 'POST',
      body: JSON.stringify({ message, channels, customer_id: customerId }),
    });
  },

  // -- Contato ativo ------------------------------------------------------
  listEligibleCustomers(onlyContactable = false): Promise<EligibleCustomer[]> {
    return request(`/api/v1/outreach/eligible${onlyContactable ? '?only_contactable=true' : ''}`);
  },

  sendOutreach(customerId: string, offerId: string,
               agent = 'Console'): Promise<OutreachResult> {
    return request('/api/v1/outreach/send', {
      method: 'POST',
      body: JSON.stringify({ customer_id: customerId, offer_id: offerId, agent }),
    });
  },

  // -- Operação -----------------------------------------------------------
  getHealth(): Promise<Health> {
    return request('/health');
  },

  getAudit(customerId?: string, limit = 50): Promise<Record<string, unknown>[]> {
    return request(`/api/v1/audit${query({ customer_id: customerId, limit: String(limit) })}`);
  },
};
