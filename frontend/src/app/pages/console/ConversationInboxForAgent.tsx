import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { Headset, Radio } from 'lucide-react';

import { useAgentInboxConversations, useNow } from '../../api/hooks';
import AgentInboxFilters, {
  type AgentInboxFilterState,
} from '../../components/agent-inbox/AgentInboxFilters';
import ConversationRowWithUrgency from '../../components/agent-inbox/ConversationRowWithUrgency';
import { ErrorState, Loading } from '../../components/AsyncBoundary';
import { cn } from '../../components/ui/utils';
import { CURRENT_AGENT } from '../../lib/agent';
import { secondsSince, urgencyLevel, type UrgencyLevel } from '../../lib/urgency';

/**
 * Inbox do Atendente — a fila de quem atende.
 *
 * O Inbox omnichannel mostra tudo o que passa pelo hub, inclusive o que o
 * assistente resolve sozinho. Aqui ficam só as conversas transferidas para um
 * humano, na ordem em que precisam ser atendidas: prioridade primeiro e, entre
 * iguais, quem está esperando há mais tempo. A ordem vem pronta da API; a tela
 * só recalcula o relógio.
 */

const SUMMARY: { level: UrgencyLevel; label: string; dot: string }[] = [
  { level: 'critical', label: 'críticas', dot: 'bg-red-600' },
  { level: 'high', label: 'urgentes', dot: 'bg-orange-500' },
  { level: 'medium', label: 'em atenção', dot: 'bg-yellow-400' },
  { level: 'low', label: 'no prazo', dot: 'bg-green-500' },
];

export default function ConversationInboxForAgent() {
  const [filters, setFilters] = useState<AgentInboxFilterState>({
    mineOnly: true, sortBy: 'priority', replyStatus: 'all',
  });
  const now = useNow(30000);
  const state = useAgentInboxConversations(
    { agent: CURRENT_AGENT, mineOnly: filters.mineOnly, sortBy: filters.sortBy }, 10000);

  const items = useMemo(() => {
    const list = state.data ?? [];
    if (filters.replyStatus === 'awaiting') return list.filter((c) => c.unread);
    if (filters.replyStatus === 'answered') return list.filter((c) => !c.unread);
    return list;
  }, [state.data, filters.replyStatus]);

  const counts = useMemo(() => {
    const result: Record<UrgencyLevel, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const c of items) {
      const seconds = secondsSince(c.handover_requested_at, now) ?? c.waiting_seconds ?? 0;
      result[urgencyLevel(seconds)] += 1;
    }
    return result;
  }, [items, now]);

  return (
    <div className="p-4 md:p-6 max-w-[1200px] mx-auto space-y-4">
      <div className="bg-white rounded-xl border border-gray-200 p-4 sticky top-0 z-10 space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
              <Headset className="w-5 h-5 text-emerald-700" aria-hidden />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">
                {items.length} conversa{items.length !== 1 ? 's' : ''} aguardando
              </h2>
              <p className="text-xs text-gray-500">
                Só transferidas para atendimento humano · ordenadas por prioridade de atendimento
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-wrap text-xs text-gray-600" aria-label="Resumo por urgência">
            {SUMMARY.map((s) => (
              <span key={s.level} className="flex items-center gap-1.5">
                <span className={cn('w-2 h-2 rounded-full', s.dot)} aria-hidden />
                <strong className="text-gray-900">{counts[s.level]}</strong> {s.label}
              </span>
            ))}
            <span className="flex items-center gap-1 text-[10px] text-gray-400">
              <Radio className="w-3 h-3 text-green-500" aria-hidden /> ao vivo
            </span>
          </div>
        </div>
        <AgentInboxFilters value={filters} onChange={setFilters} agent={CURRENT_AGENT} />
      </div>

      {state.loading && !state.data && <Loading label="Carregando a fila do atendente…" />}
      {state.error && !state.data && <ErrorState message={state.error} onRetry={state.reload} />}

      {state.data && items.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
          <Headset className="w-12 h-12 text-gray-200 mx-auto mb-3" aria-hidden />
          <h3 className="text-base font-medium text-gray-900 mb-1">Nenhuma conversa na sua fila</h3>
          <p className="text-sm text-gray-600 max-w-md mx-auto">
            Conversas aparecem aqui quando o assistente transfere o atendimento para um humano —
            por exemplo, quando o cliente pede um atendente no{' '}
            <Link to="/simulador" className="text-[#E10019] font-medium hover:underline">simulador</Link>.
          </p>
        </div>
      )}

      <ol className="space-y-3" aria-label="Fila do atendente">
        {items.map((conversation, index) => (
          <ConversationRowWithUrgency
            key={conversation.id}
            conversation={conversation}
            now={now}
            position={index + 1}
            agent={CURRENT_AGENT}
          />
        ))}
      </ol>
    </div>
  );
}
