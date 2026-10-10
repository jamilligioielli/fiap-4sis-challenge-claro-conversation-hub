import { ArrowDownUp, Filter, UserCheck } from 'lucide-react';

import type { QueueSort } from '../../api/types';
import { Switch } from '../ui/switch';

export type ReplyStatusFilter = 'all' | 'awaiting' | 'answered';

export interface AgentInboxFilterState {
  mineOnly: boolean;
  sortBy: QueueSort;
  replyStatus: ReplyStatusFilter;
}

export const SORT_OPTIONS: { value: QueueSort; label: string }[] = [
  { value: 'priority', label: 'Prioridade de atendimento' },
  { value: 'wait_time', label: 'Tempo de espera' },
  { value: 'recent', label: 'Atividade recente' },
];

export const STATUS_OPTIONS: { value: ReplyStatusFilter; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'awaiting', label: 'Aguardando resposta' },
  { value: 'answered', label: 'Respondidas' },
];

/** Controles da fila do atendente — numa linha só, acima da lista. */
export default function AgentInboxFilters({ value, onChange, agent }: {
  value: AgentInboxFilterState;
  onChange: (next: AgentInboxFilterState) => void;
  agent: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
        <Switch
          checked={value.mineOnly}
          onCheckedChange={(checked) => onChange({ ...value, mineOnly: checked })}
          aria-label="Mostrar apenas transferidas para mim"
          className="data-[state=checked]:bg-[#E10019] data-[state=unchecked]:bg-gray-300"
        />
        <UserCheck className="w-4 h-4 text-gray-500" aria-hidden />
        <span>
          Mostrar apenas transferidas para mim
          <span className="block text-[11px] text-gray-400">
            {value.mineOnly ? `${agent} + fila sem atendente` : 'todas as transferidas'}
          </span>
        </span>
      </label>

      <label className="flex items-center gap-2 text-sm text-gray-700">
        <ArrowDownUp className="w-4 h-4 text-gray-500" aria-hidden />
        <span className="sr-only sm:not-sr-only">Ordenar por</span>
        <select
          aria-label="Ordenar por"
          value={value.sortBy}
          onChange={(e) => onChange({ ...value, sortBy: e.target.value as QueueSort })}
          className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm border-0 focus:outline-none focus:ring-2 focus:ring-[#E10019] cursor-pointer"
        >
          {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-gray-700">
        <Filter className="w-4 h-4 text-gray-500" aria-hidden />
        <span className="sr-only sm:not-sr-only">Status</span>
        <select
          aria-label="Status"
          value={value.replyStatus}
          onChange={(e) => onChange({ ...value,
                                      replyStatus: e.target.value as ReplyStatusFilter })}
          className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm border-0 focus:outline-none focus:ring-2 focus:ring-[#E10019] cursor-pointer"
        >
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
    </div>
  );
}
