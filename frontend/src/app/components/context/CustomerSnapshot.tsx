import { History, Sparkles, User } from 'lucide-react';

import type {
  ConversationHistory, ConversationHistoryItem, CustomerContext, Intent,
} from '../../api/types';
import { formatDate } from '../history/historyStyles';
import { cn } from '../ui/utils';
import ConfidenceBadge from './ConfidenceBadge';
import ConsumptionBar from './ConsumptionBar';
import CustomerContextCard from './CustomerContextCard';
import NpsHistoryBadge from './NpsHistoryBadge';

/**
 * Os três cartões de contexto — Cliente, Intenção e Histórico.
 *
 * `row` põe os três lado a lado (uma coluna em telas estreitas); `stack`
 * empilha, para caber no painel lateral da conversa.
 */
export default function CustomerSnapshot({
  customer, customerError, intent, history, currentConversationId, layout = 'stack',
  onOpenHistory,
}: {
  customer: CustomerContext | null;
  /** O cadastro não pôde ser carregado (cliente não identificado, por exemplo). */
  customerError?: string | null;
  /** Intenção da conversa aberta; sem ela, o cartão mostra o último atendimento. */
  intent?: Intent | null;
  history: ConversationHistory | null;
  currentConversationId?: string;
  layout?: 'row' | 'stack';
  onOpenHistory?: () => void;
}) {
  const previous = (history?.items ?? []).filter((i) => i.id !== currentConversationId);

  return (
    <div className={cn('grid gap-3',
                       layout === 'row' ? 'grid-cols-1 md:grid-cols-3' : 'grid-cols-1')}
         data-testid="customer-snapshot">
      <CustomerCard customer={customer} error={customerError} />
      {intent !== undefined
        ? <IntentCard intent={intent} />
        : <LatestCard item={history?.items[0] ?? null} />}
      <HistoryCard previous={previous} history={history} onOpenHistory={onOpenHistory} />
    </div>
  );
}

// ------------------------------------------------------------------ cliente
function CustomerCard({ customer, error }: {
  customer: CustomerContext | null; error?: string | null;
}) {
  return (
    <CustomerContextCard icon={<User className="w-4 h-4" />} title="Cliente"
                         accent="bg-blue-50 text-blue-600">
      {!customer ? (
        <p className="text-xs text-gray-500">
          {error ? 'Cliente ainda não identificado — sem cadastro vinculado.'
                 : 'Carregando o cadastro…'}
        </p>
      ) : (
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-semibold text-gray-900 truncate">{customer.name}</p>
            <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
              {customer.segment}
            </span>
          </div>
          {customer.plan ? (
            <>
              <p className="text-xs text-gray-600">
                Plano <strong className="text-gray-900">{customer.plan.name}</strong>
              </p>
              <ConsumptionBar current={customer.plan.used_gb} total={customer.plan.data_gb} />
            </>
          ) : (
            <p className="text-xs text-gray-500">Sem plano móvel cadastrado.</p>
          )}
          <p className="text-xs text-gray-500">
            {customer.customer_since ? `Ativo desde ${customer.customer_since}` : 'Data de entrada não informada'}
            {' · '}risco de churn {customer.churn_label.toLowerCase()}
          </p>
        </div>
      )}
    </CustomerContextCard>
  );
}

// ----------------------------------------------------------------- intenção
function IntentCard({ intent }: { intent: Intent | null }) {
  const wanted = intent?.entities?.plano;
  return (
    <CustomerContextCard icon={<Sparkles className="w-4 h-4" />} title="Intenção"
                         accent="bg-green-50 text-green-600">
      {!intent ? (
        <p className="text-xs text-gray-500">Ainda sem intenção identificada nesta conversa.</p>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <p className="font-semibold text-gray-900">{intent.name}</p>
            <ConfidenceBadge score={intent.confidence} />
          </div>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>Área: <strong className="text-gray-800">{intent.area}</strong></li>
            {wanted && <li>Pedido: <strong className="text-gray-800">{wanted}</strong></li>}
            <li className="text-gray-400">
              motor: {intent.engine.startsWith('llm') ? 'modelo de linguagem' : 'regras'}
            </li>
          </ul>
        </div>
      )}
    </CustomerContextCard>
  );
}

/** Variante para fora de uma conversa: o atendimento mais recente. */
function LatestCard({ item }: { item: ConversationHistoryItem | null }) {
  return (
    <CustomerContextCard icon={<Sparkles className="w-4 h-4" />} title="Último atendimento"
                         accent="bg-green-50 text-green-600">
      {!item ? (
        <p className="text-xs text-gray-500">Nenhuma conversa registrada ainda.</p>
      ) : (
        <div className="space-y-2">
          <p className="font-semibold text-gray-900">{item.intent ?? item.type_label}</p>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>{formatDate(item.date)} · {item.type_label}</li>
            <li>Situação: <strong className="text-gray-800">{item.status_label}</strong></li>
            <li>Atendido por {item.attended_by === 'agent' ? 'humano' : 'bot'}</li>
          </ul>
        </div>
      )}
    </CustomerContextCard>
  );
}

// ---------------------------------------------------------------- histórico
function HistoryCard({ previous, history, onOpenHistory }: {
  previous: ConversationHistoryItem[];
  history: ConversationHistory | null;
  onOpenHistory?: () => void;
}) {
  const last = previous[0];
  const lastRated = previous.find((i) => i.nps_score != null);
  const frequency = history?.insights.average_frequency_days;

  return (
    <CustomerContextCard
      icon={<History className="w-4 h-4" />} title="Histórico" accent="bg-orange-50 text-orange-600"
      action={onOpenHistory && previous.length > 0 ? (
        <button type="button" onClick={onOpenHistory}
                className="text-[11px] font-medium text-[#E10019] hover:underline">
          ver linha do tempo
        </button>
      ) : undefined}
    >
      {!history ? (
        <p className="text-xs text-gray-500">Carregando o histórico…</p>
      ) : previous.length === 0 ? (
        <p className="text-xs text-gray-500">Primeiro contato deste cliente nos últimos {history.months} meses.</p>
      ) : (
        <div className="space-y-2">
          <p className="font-semibold text-gray-900">
            {previous.length} conversa{previous.length !== 1 ? 's' : ''} anterior{previous.length !== 1 ? 'es' : ''}
          </p>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>Última: {formatDate(last.date)} · {last.intent ?? last.type_label}</li>
            {frequency != null && (
              <li>Costuma voltar a cada {frequency.toFixed(1).replace('.', ',').replace(',0', '')} dia(s)</li>
            )}
          </ul>
          <div className="flex items-center gap-2 text-xs text-gray-600">
            NPS anterior:
            <NpsHistoryBadge score={lastRated?.nps_score ?? null} category={lastRated?.nps_category} />
          </div>
        </div>
      )}
    </CustomerContextCard>
  );
}
