import { useState } from 'react';
import { Link } from 'react-router';
import {
  BarChart, Bar, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import {
  MessageSquare, CheckCircle2, Users, TrendingUp, Sparkles, AlertTriangle, Info, Radio,
  BarChart3,
} from 'lucide-react';

import { useDashboard } from '../../api/hooks';
import type { Dashboard as DashboardData } from '../../api/types';
import { AsyncBoundary } from '../../components/AsyncBoundary';
import KPICard from '../../components/KPICard';
import NpsComparisonSection from '../../components/nps/NpsComparisonSection';
import { cn } from '../../components/ui/utils';

/**
 * Dashboard operacional.
 *
 * Os números vêm calculados das conversas que o hub realmente processou — não
 * de constantes. Mandar uma mensagem pelo Simulador e ver o indicador se mover
 * é a diferença entre uma tela bonita e um sistema funcionando.
 *
 * A API devolve números crus; a formatação de exibição é feita aqui, que é onde
 * se conhece o locale de quem olha.
 */

const AREAS = ['Todos', 'Suporte', 'Vendas', 'Financeiro', 'Marketing', 'Retenção', 'Técnico'];

const areaStyles: Record<string, { active: string; badge: string }> = {
  Todos:      { active: 'bg-gray-800 text-white border-gray-800',     badge: 'bg-gray-100 text-gray-600' },
  Suporte:    { active: 'bg-blue-600 text-white border-blue-600',     badge: 'bg-blue-100 text-blue-700' },
  Vendas:     { active: 'bg-green-600 text-white border-green-600',   badge: 'bg-green-100 text-green-700' },
  Financeiro: { active: 'bg-amber-600 text-white border-amber-600',   badge: 'bg-amber-100 text-amber-700' },
  Marketing:  { active: 'bg-violet-600 text-white border-violet-600', badge: 'bg-violet-100 text-violet-700' },
  Retenção:   { active: 'bg-red-600 text-white border-red-600',       badge: 'bg-red-100 text-red-700' },
  Técnico:    { active: 'bg-cyan-600 text-white border-cyan-600',     badge: 'bg-cyan-100 text-cyan-700' },
};

const impactStyles: Record<string, string> = {
  'Crítico': 'bg-red-100 text-red-700',
  'Alto': 'bg-orange-100 text-orange-700',
  'Médio': 'bg-yellow-100 text-yellow-700',
};

const compact = (value: number) =>
  value >= 1000 ? `${(value / 1000).toFixed(1).replace('.', ',')}k` : String(Math.round(value));

const percent = (value: number) => `${value.toFixed(1).replace('.', ',')}%`;

const brlCompact = (value: number) =>
  value >= 1000 ? `R$ ${Math.round(value / 1000)}k/mês`
                : `R$ ${value.toLocaleString('pt-BR')}/mês`;

export default function DashboardPage() {
  const [area, setArea] = useState('Todos');
  const state = useDashboard(area, 8000);

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-[1600px] mx-auto">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm font-medium text-gray-500">Área:</span>
        {AREAS.map((option) => {
          const style = areaStyles[option];
          const isActive = area === option;
          const count = state.data?.area_counts?.[option];
          return (
            <button
              key={option}
              onClick={() => setArea(option)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all',
                isActive ? style.active : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50',
              )}
            >
              {option}
              {!isActive && count != null && (
                <span className={cn('px-1.5 py-0.5 rounded-full text-xs font-semibold', style.badge)}>
                  {compact(count)}
                </span>
              )}
            </button>
          );
        })}
        <span className="ml-auto flex items-center gap-1.5 text-xs text-gray-400">
          <Radio className="w-3.5 h-3.5 text-green-500" />
          derivado das conversas reais · atualiza sozinho
        </span>
      </div>

      <AsyncBoundary state={state} loadingLabel="Calculando as métricas…">
        {(data) => <DashboardView data={data} area={area} />}
      </AsyncBoundary>
    </div>
  );
}

/**
 * Painel sem dado nenhum.
 *
 * Começar vazio é uma decisão, não uma falta: um dashboard pré-preenchido com
 * números inventados não prova nada sobre o sistema. Aqui o primeiro número
 * aparece quando a primeira mensagem passa pelo hub.
 */
function DashboardEmpty() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
      <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
        <BarChart3 className="w-7 h-7 text-[#E10019]" />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Nenhuma conversa processada ainda
      </h3>
      <p className="text-sm text-gray-600 max-w-lg mx-auto mb-6 leading-relaxed">
        O painel começa vazio de propósito. Cada indicador aqui é calculado sobre as
        conversas que o hub realmente atendeu — nada é semeado. Escolha um cliente no
        simulador, mande uma mensagem, e volte: o número se move.
      </p>
      <Link
        to="/simulador"
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#E10019] text-white rounded-lg text-sm font-medium hover:bg-[#C20015] transition-colors"
      >
        <Radio className="w-4 h-4" />
        Abrir o simulador
      </Link>
    </div>
  );
}

function DashboardView({ data, area }: { data: DashboardData; area: string }) {
  const channels = data.channels.filter((c) => c.value > 0);
  const totalChannel = channels.reduce((sum, c) => sum + c.value, 0);

  if (!data.has_data) return <DashboardEmpty />;

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard title="Conversas" value={compact(data.conversations.value)}
          trend={data.conversations.trend} trendLabel="vs mês anterior"
          icon={<MessageSquare className="w-5 h-5 text-[#E10019]" />} />
        <KPICard title="Taxa de Resolução" value={percent(data.resolution_rate.value)}
          trend={data.resolution_rate.trend} trendLabel="vs mês anterior"
          icon={<CheckCircle2 className="w-5 h-5 text-[#E10019]" />} />
        <KPICard title="Transferências p/ Humano" value={percent(data.handover_rate.value)}
          trend={data.handover_rate.trend} trendLabel="vs mês anterior"
          icon={<Users className="w-5 h-5 text-[#E10019]" />} />
        <KPICard title="NPS Estimado" value={compact(data.nps.value)}
          trend={data.nps.trend} trendLabel="vs mês anterior"
          icon={<TrendingUp className="w-5 h-5 text-[#E10019]" />} />
      </div>

      {/* Melhoria 1 — a nota muda quando um humano entra no atendimento? */}
      <NpsComparisonSection area={area} />

      {/* gráficos */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Distribuição por Canal</h3>
          {channels.length === 0 ? (
            <p className="text-sm text-gray-500 py-12 text-center">Sem conversas nesta área.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={channels} dataKey="value" nameKey="name" outerRadius={92}
                    label={({ name, percent: p }) => `${name} ${((p ?? 0) * 100).toFixed(0)}%`}>
                    {channels.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [`${v} conversas`, '']} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-3">
                {channels.map((entry) => (
                  <div key={entry.name} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-gray-600">
                      <span className="w-2.5 h-2.5 rounded-full"
                            style={{ backgroundColor: entry.color }} />
                      {entry.name}
                    </span>
                    <span className="text-gray-900 font-medium">
                      {entry.value}
                      <span className="text-gray-400 font-normal ml-1">
                        ({Math.round(entry.value / totalChannel * 100)}%)
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>

        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Conversas na Semana</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.week}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEF0F3" vertical={false} />
              <XAxis dataKey="day" tickLine={false} axisLine={false}
                     tick={{ fill: '#6B7280', fontSize: 12 }} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false}
                     tick={{ fill: '#6B7280', fontSize: 12 }} />
              <Tooltip cursor={{ fill: '#F9FAFB' }}
                       formatter={(v: number) => [`${v} conversas`, '']} />
              <Bar dataKey="conversations" fill="#E10019" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>

      {/* intenções */}
      {data.intents.length > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Intenções Identificadas</h3>
          <div className="space-y-2">
            {data.intents.map((intent) => {
              const max = Math.max(...data.intents.map((i) => i.count));
              return (
                <div key={intent.name} className="flex items-center gap-3">
                  <span className="w-52 text-sm text-gray-700 truncate shrink-0">{intent.name}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2.5">
                    <div className="bg-[#E10019] h-2.5 rounded-full"
                         style={{ width: `${(intent.count / max) * 100}%` }} />
                  </div>
                  <span className="w-8 text-right text-sm text-gray-900 font-medium">
                    {intent.count}
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* rupturas e automação */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Jornadas com Ruptura</h3>
            <Link to="/console/inbox" className="text-sm text-[#E10019] font-medium hover:underline">
              Ver detalhes →
            </Link>
          </div>
          {data.journey_breaks.length === 0 ? (
            <p className="text-sm text-gray-500 py-6 text-center">
              Nenhuma transferência registrada nesta área — o bot está resolvendo sozinho.
            </p>
          ) : (
            <div className="space-y-3">
              {data.journey_breaks.map((item) => (
                <div key={`${item.journey}-${item.break}`}
                     className="p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-start justify-between gap-3 mb-1">
                    <p className="font-medium text-gray-900 text-sm">{item.journey}</p>
                    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium shrink-0',
                                        impactStyles[item.impact] ?? 'bg-gray-100 text-gray-600')}>
                      {item.impact}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mb-1">Ponto de ruptura: {item.break}</p>
                  <p className="text-xs text-gray-400">{item.occurrences} ocorrência(s)</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Oportunidades de Automação</h3>
            <Link to="/console/design-studio" className="text-sm text-[#E10019] font-medium hover:underline">
              Configurar →
            </Link>
          </div>
          {data.automation_opportunities.length === 0 ? (
            <p className="text-sm text-gray-500 py-6 text-center">
              Ainda sem volume suficiente para estimar.
            </p>
          ) : (
            <div className="space-y-3">
              {data.automation_opportunities.map((item) => (
                <div key={item.area}
                  className="p-3 rounded-lg bg-gradient-to-r from-red-50 to-orange-50 border border-red-100">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="w-4 h-4 text-[#E10019]" />
                    <p className="font-medium text-gray-900 text-sm">{item.area}</p>
                  </div>
                  <p className="text-xs text-gray-600">
                    Contenção digital atual: {item.potential}%
                  </p>
                  <p className="text-xs text-gray-600">
                    Economia estimada: {brlCompact(item.estimated_savings_brl)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* alertas */}
      {data.alerts.length > 0 && (
        <section className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Alertas Operacionais</h3>
          <div className="space-y-3">
            {data.alerts.map((alert) => {
              const warning = alert.severity === 'warning';
              const Icon = warning ? AlertTriangle : Info;
              return (
                <div key={alert.title}
                  className={cn('p-3 rounded-lg border flex items-start gap-3',
                    warning ? 'bg-amber-50 border-amber-200' : 'bg-blue-50 border-blue-200')}>
                  <Icon className={cn('w-4 h-4 mt-0.5 shrink-0',
                                      warning ? 'text-amber-600' : 'text-blue-600')} />
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{alert.title}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{alert.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
