import { Bot, Headset } from 'lucide-react';

import type { NpsComparison, NpsGroup } from '../../api/types';
import { cn } from '../ui/utils';
import { CATEGORIES, SERIES, type SeriesKey, pct, score, signed } from './format';

/**
 * Dois cartões lado a lado: nota média e distribuição do NPS de quem foi
 * atendido só pelo assistente e de quem passou por um atendente humano.
 */
export default function NpsComparisonCards({ data }: { data: NpsComparison }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <NpsGroupCard kind="bot" group={data.bot} />
      <NpsGroupCard kind="agent" group={data.agent} />
    </div>
  );
}

function NpsGroupCard({ kind, group }: { kind: SeriesKey; group: NpsGroup }) {
  const series = SERIES[kind];
  const Icon = kind === 'bot' ? Bot : Headset;
  const title = kind === 'bot' ? 'Atendido pelo bot' : 'Atendido por humano';

  return (
    <article
      aria-label={`NPS — ${title}`}
      className="rounded-xl border border-gray-200 bg-white p-5"
      style={{ borderTop: `4px solid ${series.color}` }}
    >
      <header className="flex items-center gap-2 mb-4">
        <span className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: `${series.color}1A`, color: series.color }}>
          <Icon className="w-4 h-4" aria-hidden />
        </span>
        <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">{title}</h4>
      </header>

      {group.total === 0 ? (
        <p className="text-sm text-gray-500 py-6">
          Ainda sem notas neste grupo.
          {group.surveys_sent > 0 && ` ${group.surveys_sent} pesquisa(s) enviada(s), sem resposta.`}
        </p>
      ) : (
        <>
          <div className="flex items-end gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500">Nota média</p>
              <p className="text-4xl font-semibold text-gray-900 leading-tight">
                {score(group.average_score)}
                <span className="text-base font-normal text-gray-400">/10</span>
              </p>
            </div>
            <div className="pb-1">
              <p className="text-xs text-gray-500">NPS</p>
              <p className="text-xl font-semibold text-gray-900">{signed(group.nps)}</p>
            </div>
          </div>

          <ul className="space-y-1.5 text-sm">
            {CATEGORIES.map((category) => (
              <li key={category.key} className="flex items-center gap-2"
                  title={`${category.label}: notas ${category.range}`}>
                <span className={cn('w-2.5 h-2.5 rounded-full shrink-0', category.dot)}
                      aria-hidden />
                <span className="text-gray-700">{category.label}</span>
                <span className="ml-auto font-medium text-gray-900">
                  {pct(group.percentages[category.key])}
                </span>
                <span className="w-8 text-right text-xs text-gray-500">{group[category.key]}</span>
              </li>
            ))}
          </ul>

          <p className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500">
            {group.total} resposta{group.total !== 1 ? 's' : ''}
            {group.unanswered > 0 && ` · ${group.unanswered} pesquisa(s) sem resposta`}
          </p>
        </>
      )}
    </article>
  );
}
