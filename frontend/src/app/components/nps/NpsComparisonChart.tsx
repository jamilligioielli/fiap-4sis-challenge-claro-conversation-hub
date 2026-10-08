import {
  Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import type { NpsComparison } from '../../api/types';
import { CATEGORIES, SERIES, pct } from './format';

interface Row {
  category: string;
  bot: number;
  agent: number;
  botCount: number;
  agentCount: number;
}

/**
 * Distribuição do NPS por categoria, bot versus atendente.
 *
 * Em percentual, e não em contagem: os dois grupos raramente têm o mesmo
 * tamanho, e comparar 12 promotores de 40 com 5 de 8 em número absoluto leva
 * à conclusão errada. A contagem continua no tooltip.
 */
export function toRows(data: NpsComparison): Row[] {
  return CATEGORIES.map((category) => ({
    category: category.label,
    bot: data.bot.percentages[category.key],
    agent: data.agent.percentages[category.key],
    botCount: data.bot[category.key],
    agentCount: data.agent[category.key],
  }));
}

export default function NpsComparisonChart({ data }: { data: NpsComparison }) {
  const rows = toRows(data);

  return (
    <figure aria-label="Distribuição do NPS: bot versus atendente">
      <div className="flex items-center gap-4 mb-2 text-xs text-gray-600" role="list"
           aria-label="Legenda">
        {(['bot', 'agent'] as const).map((key) => (
          <span key={key} role="listitem" className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: SERIES[key].color }}
                  aria-hidden />
            {SERIES[key].label}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows} layout="vertical" barGap={2} barCategoryGap="24%"
                  margin={{ top: 4, right: 48, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`}
                 tickLine={false} axisLine={false} tick={{ fill: '#6B7280', fontSize: 12 }} />
          <YAxis type="category" dataKey="category" width={88} tickLine={false} axisLine={false}
                 tick={{ fill: '#374151', fontSize: 12 }} />
          <Tooltip
            cursor={{ fill: '#F9FAFB' }}
            formatter={(value: number, name: string, item) => {
              const row = item.payload as Row;
              const count = name === SERIES.bot.label ? row.botCount : row.agentCount;
              return [`${pct(value)} (${count})`, name];
            }}
          />
          {(['bot', 'agent'] as const).map((key) => (
            <Bar key={key} dataKey={key} name={SERIES[key].label} fill={SERIES[key].color}
                 radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false}>
              <LabelList dataKey={key} position="right"
                         formatter={(v: number) => pct(v)}
                         style={{ fill: '#374151', fontSize: 11 }} />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
      <figcaption className="sr-only">
        {rows.map((r) => `${r.category}: bot ${pct(r.bot)}, atendente ${pct(r.agent)}`).join('; ')}
      </figcaption>
    </figure>
  );
}
