/**
 * Hooks de acesso à API.
 *
 * Cada tela recebe `{ data, error, loading, reload }` e nada mais — não sabe se
 * o dado veio de fetch, cache ou websocket. É a mesma separação que o back-end
 * faz com as portas, aplicada do lado do cliente.
 *
 * `pollMs` existe para a demonstração: com o Inbox atualizando sozinho, dá para
 * mandar uma mensagem pelo simulador e vê-la aparecer na fila sem tocar na tela.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { api, ApiError } from './client';
import type {
  ConversationDetail, ConversationHistory, ConversationListItem, CustomerContext, CustomerSummary,
  Dashboard, EligibleCustomer, Health, NpsComparison, QueueSort, StudioConfig,
  WhatsAppStatus,
} from './types';

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

function useAsync<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
  pollMs?: number,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const alive = useRef(true);

  // Guardamos o fetcher numa ref para que mudar a identidade da função entre
  // renders não dispare uma nova requisição — só as deps declaradas disparam.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    alive.current = true;
    let cancelled = false;

    (async () => {
      try {
        const result = await fetcherRef.current();
        if (!cancelled && alive.current) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (!cancelled && alive.current) {
          setError(err instanceof ApiError ? err.message : 'Erro inesperado ao consultar a API.');
        }
      } finally {
        if (!cancelled && alive.current) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  useEffect(() => () => { alive.current = false; }, []);

  useEffect(() => {
    if (!pollMs) return;
    const id = setInterval(() => setTick((t) => t + 1), pollMs);
    return () => clearInterval(id);
  }, [pollMs]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}

export function useConversations(
  filters: { area?: string; channel?: string; status?: string; search?: string },
  pollMs?: number,
): AsyncState<ConversationListItem[]> {
  const { area, channel, status, search } = filters;
  return useAsync(
    () => api.listConversations({ area, channel, status, search }),
    [area, channel, status, search],
    pollMs,
  );
}

/**
 * Fila do atendente. `mineOnly` liga o filtro "transferidas para mim" — que
 * inclui a fila ainda sem dono, de onde o atendente puxa o próximo caso.
 */
export function useAgentInboxConversations(
  filters: { agent: string; mineOnly: boolean; sortBy: QueueSort },
  pollMs?: number,
): AsyncState<ConversationListItem[]> {
  const { agent, mineOnly, sortBy } = filters;
  return useAsync(
    () => api.listAgentQueue({ agent: mineOnly ? agent : undefined, sortBy }),
    [agent, mineOnly, sortBy],
    pollMs,
  );
}

/**
 * Relógio da tela. Recalcula tempos de espera sem buscar nada na API — o
 * tempo passa no navegador, não no servidor.
 */
export function useNow(intervalMs = 30000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function useConversation(id: string | undefined, pollMs?: number)
  : AsyncState<ConversationDetail> {
  return useAsync(
    () => (id ? api.getConversation(id) : Promise.reject(new ApiError(404, 'Sem conversa'))),
    [id],
    pollMs,
  );
}

export function useCustomerContext(customerId: string | undefined)
  : AsyncState<CustomerContext> {
  return useAsync(
    () => (customerId
      ? api.getCustomerContext(customerId)
      : Promise.reject(new ApiError(404, 'Sem cliente'))),
    [customerId],
  );
}

/**
 * Histórico de conversas do cliente.
 *
 * Sem polling: cada leitura entra na trilha de auditoria, e consultar o
 * histórico a cada poucos segundos encheria a trilha de acessos que ninguém
 * fez. `version` recarrega quando a conversa aberta muda de fato.
 */
export function useCustomerConversationHistory(
  customerId: string | undefined, version: string | number = 0, months = 6,
): AsyncState<ConversationHistory> {
  return useAsync(
    () => (customerId
      ? api.getConversationHistory(customerId, months)
      : Promise.reject(new ApiError(404, 'Sem cliente'))),
    [customerId, version, months],
  );
}

export function useDashboard(area: string | undefined, pollMs?: number): AsyncState<Dashboard> {
  const scoped = area && area !== 'Todos' ? area : undefined;
  return useAsync(() => api.getDashboard(scoped), [scoped], pollMs);
}

/** Mesmo recorte de área do painel — trocar o filtro move os dois juntos. */
export function useNpsComparison(area: string | undefined, pollMs?: number)
  : AsyncState<NpsComparison> {
  const scoped = area && area !== 'Todos' ? area : undefined;
  return useAsync(() => api.getNpsComparison(scoped), [scoped], pollMs);
}

export function useStudioConfig(): AsyncState<StudioConfig> {
  return useAsync(() => api.getStudioConfig(), []);
}

export function useHealth(pollMs = 30000): AsyncState<Health> {
  return useAsync(() => api.getHealth(), [], pollMs);
}

export function useWhatsAppStatus(): AsyncState<WhatsAppStatus> {
  return useAsync(() => api.getWhatsAppStatus(), []);
}

export function useCustomers(): AsyncState<CustomerSummary[]> {
  return useAsync(() => api.listCustomers(), []);
}

export function useCustomerConversations(customerId: string | undefined)
  : AsyncState<ConversationListItem[]> {
  return useAsync(
    () => (customerId
      ? api.listCustomerConversations(customerId)
      : Promise.reject(new ApiError(404, 'Sem cliente'))),
    [customerId],
  );
}

export function useEligibleCustomers(onlyContactable = false)
  : AsyncState<EligibleCustomer[]> {
  return useAsync(() => api.listEligibleCustomers(onlyContactable), [onlyContactable]);
}
