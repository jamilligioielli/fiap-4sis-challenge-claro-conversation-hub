import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { Search, ChevronRight, MessageCircle, Phone, Globe, Smartphone, Radio } from 'lucide-react';

import { useConversations } from '../api/hooks';
import type { Area, Channel, ConversationListItem } from '../api/types';
import { ErrorState, Loading } from '../components/AsyncBoundary';
import { cn } from '../components/ui/utils';

/**
 * Fila única com as conversas de todos os canais.
 *
 * A lista vem da API e se atualiza sozinha a cada 5s — mandar uma mensagem pelo
 * Simulador e vê-la surgir aqui, sem tocar na tela, é a forma mais direta de
 * mostrar que back-end e front-end são o mesmo sistema.
 */

const ALL_AREAS: (Area | 'Todos')[] =
  ['Todos', 'Suporte', 'Vendas', 'Financeiro', 'Marketing', 'Retenção', 'Técnico'];

const areaStyles: Record<string, { active: string; dot: string; badge: string }> = {
  Todos:      { active: 'bg-gray-800 text-white border-gray-800',     dot: 'bg-gray-400',   badge: 'bg-gray-100 text-gray-600' },
  Suporte:    { active: 'bg-blue-600 text-white border-blue-600',     dot: 'bg-blue-500',   badge: 'bg-blue-100 text-blue-700' },
  Vendas:     { active: 'bg-green-600 text-white border-green-600',   dot: 'bg-green-500',  badge: 'bg-green-100 text-green-700' },
  Financeiro: { active: 'bg-amber-600 text-white border-amber-600',   dot: 'bg-amber-500',  badge: 'bg-amber-100 text-amber-700' },
  Marketing:  { active: 'bg-violet-600 text-white border-violet-600', dot: 'bg-violet-500', badge: 'bg-violet-100 text-violet-700' },
  Retenção:   { active: 'bg-red-600 text-white border-red-600',       dot: 'bg-red-500',    badge: 'bg-red-100 text-red-700' },
  Técnico:    { active: 'bg-cyan-600 text-white border-cyan-600',     dot: 'bg-cyan-500',   badge: 'bg-cyan-100 text-cyan-700' },
};

const channelStyles: Record<Channel, { icon: typeof MessageCircle; color: string; bg: string; label: string }> = {
  whatsapp: { icon: MessageCircle, color: 'text-green-600',  bg: 'bg-green-50',  label: 'WhatsApp' },
  web:      { icon: Globe,         color: 'text-blue-600',   bg: 'bg-blue-50',   label: 'Web Chat' },
  app:      { icon: Smartphone,    color: 'text-red-600',    bg: 'bg-red-50',    label: 'App' },
  voice:    { icon: Phone,         color: 'text-purple-600', bg: 'bg-purple-50', label: 'Voz' },
};

const statusStyles = {
  active:      { label: 'Em atendimento',     color: 'bg-green-100 text-green-700' },
  waiting:     { label: 'Aguardando cliente', color: 'bg-yellow-100 text-yellow-700' },
  transferred: { label: 'Transferida',        color: 'bg-blue-100 text-blue-700' },
  pending:     { label: 'Pendente',           color: 'bg-gray-100 text-gray-700' },
};

const CHANNEL_FILTERS = [
  { value: '', label: 'Todos os canais' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'web', label: 'Web Chat' },
  { value: 'app', label: 'App' },
  { value: 'voice', label: 'Voz' },
];

export default function Inbox() {
  const [activeArea, setActiveArea] = useState<Area | 'Todos'>('Todos');
  const [channelFilter, setChannelFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // A contagem por área precisa do total, não do filtrado — por isso duas consultas.
  const all = useConversations({}, 5000);
  const filtered = useConversations(
    {
      area: activeArea === 'Todos' ? undefined : activeArea,
      channel: channelFilter || undefined,
      search: search || undefined,
    },
    5000,
  );

  const counts = useMemo(() => {
    const list = all.data ?? [];
    const result: Record<string, number> = { Todos: list.length };
    for (const area of ALL_AREAS.slice(1)) {
      result[area] = list.filter((c) => c.area === area).length;
    }
    return result;
  }, [all.data]);

  const items = filtered.data ?? [];
  const selected = items.find((c) => c.id === selectedId) ?? items[0] ?? null;

  return (
    <div className="h-full flex">
      {/* -------------------------------------------------- lista */}
      <div className="w-96 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-200 space-y-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar conversas..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:border-transparent"
            />
          </div>
          <select
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
            className="w-full px-3 py-1.5 bg-gray-100 rounded-lg text-sm text-gray-700 hover:bg-gray-200 transition-colors cursor-pointer border-0 focus:outline-none focus:ring-2 focus:ring-[#E10019]"
          >
            {CHANNEL_FILTERS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="px-4 py-3 border-b border-gray-200">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Área</p>
          <div className="flex flex-wrap gap-1.5">
            {ALL_AREAS.map((area) => {
              const style = areaStyles[area];
              const isActive = activeArea === area;
              return (
                <button
                  key={area}
                  onClick={() => setActiveArea(area)}
                  className={cn(
                    'flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border transition-all',
                    isActive ? style.active
                             : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50',
                  )}
                >
                  {area}
                  <span className={cn('px-1.5 py-0.5 rounded-full text-xs font-semibold',
                                      isActive ? 'bg-white/20 text-white' : style.badge)}>
                    {counts[area] ?? 0}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
          <p className="text-xs text-gray-500">
            {items.length} conversa{items.length !== 1 ? 's' : ''}
            {activeArea !== 'Todos' && (
              <span className="font-medium text-gray-700"> · {activeArea}</span>
            )}
          </p>
          <span className="ml-auto flex items-center gap-1 text-[10px] text-gray-400">
            <Radio className="w-3 h-3 text-green-500" />
            ao vivo
          </span>
        </div>

        <div className="flex-1 overflow-y-auto">
          {filtered.loading && !filtered.data && <Loading label="Carregando a fila…" />}
          {filtered.error && !filtered.data && (
            <ErrorState message={filtered.error} onRetry={filtered.reload} />
          )}
          {filtered.data && items.length === 0 && (
            <div className="flex flex-col items-center justify-center h-40 text-center px-4">
              <MessageCircle className="w-10 h-10 text-gray-200 mb-2" />
              <p className="text-sm text-gray-500">Nenhuma conversa encontrada</p>
            </div>
          )}

          {items.map((conv) => (
            <ConversationRow
              key={conv.id}
              conversation={conv}
              selected={selected?.id === conv.id}
              onSelect={() => setSelectedId(conv.id)}
            />
          ))}
        </div>
      </div>

      {/* -------------------------------------------------- detalhe */}
      <div className="flex-1 flex items-center justify-center bg-gray-50 p-6">
        {selected ? <SelectedPreview conversation={selected} /> : (
          <div className="text-center">
            <MessageCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Nenhuma conversa selecionada</h3>
            <p className="text-sm text-gray-600">Selecione uma conversa para ver os detalhes</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationRow({ conversation, selected, onSelect }: {
  conversation: ConversationListItem; selected: boolean; onSelect: () => void;
}) {
  const channel = channelStyles[conversation.channel];
  const Icon = channel.icon;
  const status = statusStyles[conversation.status];

  return (
    <div
      onClick={onSelect}
      className={cn(
        'p-4 border-b border-gray-100 cursor-pointer transition-colors',
        selected ? 'bg-red-50 border-l-4 border-l-[#E10019]' : 'hover:bg-gray-50',
        conversation.unread && !selected && 'bg-blue-50',
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn('w-10 h-10 rounded-full flex items-center justify-center shrink-0',
                            channel.bg)}>
          <Icon className={cn('w-5 h-5', channel.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <h4 className={cn('text-sm font-medium truncate',
                              conversation.unread ? 'text-gray-900' : 'text-gray-700')}>
              {conversation.customer_name}
            </h4>
            <span className="text-xs text-gray-500 ml-2 whitespace-nowrap">
              {conversation.timestamp}
            </span>
          </div>
          <p className={cn('text-sm truncate mb-2',
                           conversation.unread ? 'text-gray-900 font-medium' : 'text-gray-600')}>
            {conversation.last_message}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', status.color)}>
              {status.label}
            </span>
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <span className={cn('w-1.5 h-1.5 rounded-full inline-block shrink-0',
                                  areaStyles[conversation.area].dot)} />
              {conversation.area}
            </span>
            {conversation.priority === 'high' && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                Urgente
              </span>
            )}
            {conversation.channels_used.length > 1 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                {conversation.channels_used.length} canais
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SelectedPreview({ conversation }: { conversation: ConversationListItem }) {
  const channel = channelStyles[conversation.channel];
  const Icon = channel.icon;

  return (
    <div className="text-center max-w-sm">
      <div className={cn('w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center',
                          channel.bg)}>
        <Icon className={cn('w-8 h-8', channel.color)} />
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-1">{conversation.customer_name}</h3>

      <div className="flex items-center justify-center gap-2 mb-1 flex-wrap">
        <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium',
                            statusStyles[conversation.status].color)}>
          {statusStyles[conversation.status].label}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className={cn('w-1.5 h-1.5 rounded-full',
                              areaStyles[conversation.area].dot)} />
          {conversation.area}
        </span>
      </div>

      {conversation.intent && (
        <p className="text-xs text-gray-500 mt-2">
          Intenção: <span className="font-medium text-gray-700">{conversation.intent}</span>
          {conversation.confidence != null && ` · ${Math.round(conversation.confidence * 100)}%`}
        </p>
      )}

      {conversation.channels_used.length > 1 && (
        <p className="text-xs text-blue-600 mt-1">
          Jornada: {conversation.channels_used.map((c) => channelStyles[c].label).join(' → ')}
        </p>
      )}

      <p className="text-sm text-gray-600 mb-6 mt-3 px-4">{conversation.last_message}</p>

      <Link
        to={`/conversation/${conversation.id}`}
        className="inline-flex items-center gap-2 px-6 py-3 bg-[#E10019] text-white rounded-lg hover:bg-[#C20015] transition-colors font-medium text-sm"
      >
        Abrir conversa
        <ChevronRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
