import type { ReactNode } from 'react';
import { CalendarClock, CheckCheck, Repeat, Star } from 'lucide-react';

import type { ConversationInsights } from '../../api/types';
import NpsHistoryBadge from '../context/NpsHistoryBadge';

const decimal = (value: number) =>
  Number.isInteger(value) ? String(value) : value.toFixed(1).replace('.', ',');

/** O que a linha do tempo significa para quem vai atender agora. */
export default function ConversationTimelineInsights({ insights, months }: {
  insights: ConversationInsights; months: number;
}) {
  if (insights.total_conversations === 0) return null;

  const frequency = insights.average_frequency_days == null
    ? 'Só uma conversa no período'
    : insights.average_frequency_days < 1
      ? 'Mais de uma vez por dia'
      : `A cada ${decimal(insights.average_frequency_days)} dia${insights.average_frequency_days === 1 ? '' : 's'}`;

  return (
    <section aria-label="Indicadores do histórico" className="mt-2">
      <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
        Últimos {months} meses · {insights.total_conversations} conversa{insights.total_conversations !== 1 ? 's' : ''}
      </h5>
      <dl className="grid grid-cols-2 gap-2">
        <Insight icon={<CalendarClock className="w-3.5 h-3.5" />} label="Retorna">
          {frequency}
        </Insight>
        <Insight icon={<Repeat className="w-3.5 h-3.5" />} label="Assunto mais comum">
          {insights.most_common_type_label ?? '—'}
        </Insight>
        <Insight icon={<Star className="w-3.5 h-3.5" />} label="NPS médio">
          <NpsHistoryBadge score={insights.average_nps} category={insights.average_nps_category} />
        </Insight>
        <Insight icon={<CheckCheck className="w-3.5 h-3.5" />} label="Taxa de resolução">
          {insights.resolution_rate == null ? 'Nenhuma encerrada'
            : `${decimal(insights.resolution_rate)}%`}
        </Insight>
      </dl>
    </section>
  );
}

function Insight({ icon, label, children }: {
  icon: ReactNode; label: string; children: ReactNode;
}) {
  return (
    <div className="rounded-lg bg-gray-50 border border-gray-100 p-2.5 min-w-0">
      <dt className="flex items-center gap-1 text-[11px] text-gray-500">
        <span aria-hidden>{icon}</span>{label}
      </dt>
      <dd className="text-sm font-semibold text-gray-900 mt-0.5">{children}</dd>
    </div>
  );
}
