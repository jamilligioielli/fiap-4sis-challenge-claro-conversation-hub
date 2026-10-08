import { useState } from 'react';
import { Link, useParams } from 'react-router';
import {
  Globe, MessageCircle, Smartphone, Phone, ArrowRight, User, Send,
  UserPlus, ChevronRight, Loader2, Bot, Headset, Info, CheckCircle2, Star, CalendarDays,
} from 'lucide-react';

import { api } from '../../api/client';
import {
  useConversation, useCustomerContext, useCustomerConversationHistory,
} from '../../api/hooks';
import type {
  Channel, ConversationDetail, ConversationHistoryItem, Message,
} from '../../api/types';
import { AsyncBoundary } from '../../components/AsyncBoundary';
import CustomerSnapshot from '../../components/context/CustomerSnapshot';
import ConversationHistoryModal from '../../components/history/ConversationHistoryModal';
import ConversationTimeline from '../../components/history/ConversationTimeline';
import ConversationTimelineInsights from '../../components/history/ConversationTimelineInsights';
import MessageSentimentBadge from '../../components/sentiment/MessageSentimentBadge';
import SentimentIndicator from '../../components/sentiment/SentimentIndicator';
import { CURRENT_AGENT } from '../../lib/agent';
import { cn } from '../../components/ui/utils';

/**
 * Conversa Ativa — a tela onde o atendente assume o caso.
 *
 * O painel lateral é o que torna o handover barato: intenção, resumo, próximas
 * ações e insights chegam prontos do hub, para que o atendente não precise ler
 * a conversa inteira nem pedir que o cliente repita nada.
 */

const channelIcons: Record<Channel, typeof Globe> = {
  web: Globe, whatsapp: MessageCircle, app: Smartphone, voice: Phone,
};

const channelLabels: Record<Channel, string> = {
  web: 'Web Chat', whatsapp: 'WhatsApp', app: 'App Claro', voice: 'Voz (URA)',
};

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  const state = useConversation(id, 4000);

  return (
    <AsyncBoundary state={state} loadingLabel="Carregando a conversa…">
      {(detail) => <ConversationView detail={detail} reload={state.reload} />}
    </AsyncBoundary>
  );
}

function ConversationView({ detail, reload }: {
  detail: ConversationDetail; reload: () => void;
}) {
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [tab, setTab] = useState<'contexto' | 'historico'>('contexto');
  const [historyItem, setHistoryItem] = useState<ConversationHistoryItem | null>(null);
  const customer = useCustomerContext(detail.customer_id);
  // Recarrega o histórico quando a situação da conversa muda (transferida,
  // encerrada), não a cada mensagem: cada leitura entra na trilha de auditoria.
  const history = useCustomerConversationHistory(detail.customer_id, detail.status);

  const startedAt = new Date(detail.started_at);
  const assignedAgent = detail.ai.handover.assigned_agent;
  // Transferida pelo assistente e ainda sem dono: está na fila esperando alguém.
  const waitingForAgent = detail.status === 'transferred' && assignedAgent === null;
  const transition = detail.channels_used.length > 1;

  async function sendReply() {
    if (!draft.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      await api.replyAsAgent(detail.id, draft.trim());
      setDraft('');
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao enviar');
    } finally {
      setBusy(false);
    }
  }

  const [closed, setClosed] = useState<string | null>(null);

  /** Encerra o atendimento e dispara a pesquisa de satisfação. */
  async function close() {
    setBusy(true); setError(null);
    try {
      const resultado = await api.closeConversation(detail.id, CURRENT_AGENT);
      setClosed(resultado.survey_message);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao encerrar');
    } finally {
      setBusy(false);
    }
  }

  async function handover() {
    setBusy(true); setError(null);
    try {
      await api.requestHandover(detail.id, 'Assumido pelo atendente no console', CURRENT_AGENT);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao transferir');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-full flex flex-col lg:flex-row overflow-y-auto lg:overflow-hidden">
      {/* ------------------------------------------------ transcrição */}
      <div className="flex-1 flex flex-col bg-white min-w-0 min-h-[70vh] lg:min-h-0">
        <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-[#E10019] flex items-center justify-center text-white font-semibold">
                {initials(detail.customer_name)}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{detail.customer_name}</h3>
                <div className="flex flex-wrap items-center gap-x-2 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    <span className={cn('w-2 h-2 rounded-full',
                      detail.status === 'transferred' ? 'bg-blue-500' : 'bg-green-500')} />
                    {detail.status === 'transferred' ? 'Transferida' : 'Ativa'}
                  </span>
                  <span>•</span>
                  <span>Iniciada {relative(startedAt)}</span>
                  <span>•</span>
                  <span>{detail.area}</span>
                </div>
              </div>
            </div>
            <Link
              to={`/console/customer-context/${detail.customer_id}`}
              className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center gap-2"
            >
              <User className="w-4 h-4" />
              Ver contexto completo
            </Link>
          </div>

          {transition && (
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
              {detail.channels_used.map((channel, index) => {
                const Icon = channelIcons[channel];
                return (
                  <span key={`${channel}-${index}`} className="flex items-center gap-3">
                    <Icon className="w-5 h-5 text-blue-600" />
                    {index < detail.channels_used.length - 1 && (
                      <ArrowRight className="w-4 h-4 text-blue-600" />
                    )}
                  </span>
                );
              })}
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Transição de canal sem perda de contexto
                </p>
                <p className="text-xs text-gray-600">
                  {detail.channels_used.map((c) => channelLabels[c]).join(' → ')} mantendo
                  histórico completo
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {detail.messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>

        <div className="p-4 bg-white border-t border-gray-200">
          {error && <p className="mb-2 text-sm text-[#E10019]">{error}</p>}
          <div className="flex items-center gap-3">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') sendReply(); }}
              placeholder="Responder como atendente…"
              disabled={busy}
              className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:border-transparent disabled:opacity-60"
            />
            <button
              onClick={sendReply}
              aria-label="Enviar resposta"
              disabled={busy || !draft.trim()}
              className="p-3 bg-[#E10019] text-white rounded-lg hover:bg-[#C20015] transition-colors disabled:opacity-40"
            >
              {busy ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </div>
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <button
              onClick={handover}
              disabled={busy || assignedAgent !== null || detail.status === 'pending'}
              className={cn('px-4 py-2 rounded-lg transition-colors text-sm font-medium flex items-center gap-2 disabled:opacity-40',
                waitingForAgent ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200')}
            >
              <UserPlus className="w-4 h-4" />
              {assignedAgent
                ? (assignedAgent === CURRENT_AGENT ? 'Com você' : `Com ${assignedAgent}`)
                : waitingForAgent ? 'Assumir atendimento' : 'Assumir como humano'}
            </button>
            <button
              onClick={close}
              disabled={busy || detail.status === 'pending'}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium flex items-center gap-2 disabled:opacity-40"
            >
              <CheckCircle2 className="w-4 h-4" />
              {detail.status === 'pending' ? 'Encerrada' : 'Encerrar atendimento'}
            </button>
            <span className="text-xs text-gray-500">
              A resposta sai pelo último canal usado pelo cliente
              {detail.channels_used.length > 0 &&
                ` (${channelLabels[detail.channels_used[detail.channels_used.length - 1]]})`}
            </span>
          </div>

          {/* O encerramento dispara a pesquisa igual ao do bot: medir só o
              atendimento automatizado deixaria cego o canal mais caro. */}
          {closed && (
            <div className="mt-3 px-3 py-2 bg-violet-50 border border-violet-200 rounded-lg">
              <p className="text-xs font-medium text-violet-900 flex items-center gap-1.5 mb-1">
                <Star className="w-3.5 h-3.5" />
                Pesquisa de satisfação enviada ao cliente
              </p>
              <p className="text-xs text-violet-800 italic">"{closed}"</p>
            </div>
          )}
        </div>
      </div>

      {/* ------------------------------------- painel de contexto do atendente */}
      <aside className="w-full lg:w-[400px] bg-gradient-to-br from-gray-50 to-white border-t lg:border-t-0 lg:border-l border-gray-200 overflow-y-auto shrink-0">
        <div role="tablist" aria-label="Painel do atendente"
             className="sticky top-0 z-10 flex bg-white/95 backdrop-blur border-b border-gray-200 px-4">
          {([['contexto', 'Contexto'], ['historico', 'Histórico']] as const).map(([key, label]) => (
            <button key={key} role="tab" type="button" aria-selected={tab === key}
                    onClick={() => setTab(key)}
                    className={cn('px-3 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                      tab === key ? 'border-[#E10019] text-[#E10019]'
                                  : 'border-transparent text-gray-500 hover:text-gray-800')}>
              {key === 'historico' && <CalendarDays className="w-4 h-4 inline mr-1 -mt-0.5" aria-hidden />}
              {label}
              {key === 'historico' && history.data && history.data.items.length > 0 && (
                <span className="ml-1.5 text-[11px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  {history.data.items.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {tab === 'historico' ? (
          <div className="p-5 space-y-4" role="tabpanel" aria-label="Histórico">
            {history.loading && !history.data && (
              <p className="text-sm text-gray-500 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Carregando o histórico…
              </p>
            )}
            {history.error && !history.data && (
              <p className="text-sm text-gray-500">Histórico indisponível: {history.error}</p>
            )}
            {history.data && (
              <>
                <ConversationTimeline items={history.data.items} currentId={detail.id}
                                      onSelect={setHistoryItem} />
                <ConversationTimelineInsights insights={history.data.insights}
                                              months={history.data.months} />
              </>
            )}
          </div>
        ) : (
        <div className="p-5 space-y-5" role="tabpanel" aria-label="Contexto">
          {/* Melhoria 4 — o humor vem antes de tudo: muda a forma de abrir a conversa. */}
          <SentimentIndicator sentiment={detail.sentiment} score={detail.sentiment_score} />

          {/* Melhoria 3 — contexto em cartões escaneáveis. */}
          <CustomerSnapshot
            customer={customer.data}
            customerError={customer.error}
            intent={detail.ai.intent}
            history={history.data}
            currentConversationId={detail.id}
            onOpenHistory={() => setTab('historico')}
          />

          <section className="bg-white rounded-xl border border-gray-200 p-4">
            <h4 className="font-semibold text-gray-900 mb-3">Resumo Automático</h4>
            <div className="space-y-2 text-sm text-gray-700">
              {Object.entries(detail.ai.summary).map(([key, value]) => (
                <p key={key}>
                  <strong className="capitalize">{key.replace(/_/g, ' ')}:</strong> {value}
                </p>
              ))}
            </div>
          </section>

          {detail.ai.suggestions.length > 0 && (
            <section className="bg-white rounded-xl border border-gray-200 p-4">
              <h4 className="font-semibold text-gray-900 mb-3">Próximas Melhores Ações</h4>
              <div className="space-y-2">
                {detail.ai.suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setDraft(suggestion)}
                    className="w-full text-left p-3 bg-gradient-to-r from-red-50 to-orange-50 hover:from-red-100 hover:to-orange-100 rounded-lg text-sm text-gray-700 transition-all hover:shadow-md"
                  >
                    <div className="flex items-start gap-2">
                      <ChevronRight className="w-4 h-4 text-[#E10019] mt-0.5 shrink-0" />
                      <span>{suggestion}</span>
                    </div>
                  </button>
                ))}
              </div>
            </section>
          )}

          {detail.ai.insights.length > 0 && (
            <section className="bg-white rounded-xl border border-gray-200 p-4">
              <h4 className="font-semibold text-gray-900 mb-3">Insights do Cliente</h4>
              <div className="space-y-3 text-sm">
                {detail.ai.insights.map((insight) => (
                  <div key={insight.text} className="flex items-center gap-2">
                    <span className={cn('w-2 h-2 rounded-full shrink-0',
                      insight.tone === 'positive' ? 'bg-green-500'
                        : insight.tone === 'warning' ? 'bg-orange-500' : 'bg-blue-500')} />
                    <span className="text-gray-700">{insight.text}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className={cn('rounded-xl p-4 border',
            detail.ai.handover.requested
              ? 'bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200'
              : 'bg-white border-gray-200')}>
            <h4 className="font-semibold text-gray-900 mb-2">Status de Handover</h4>
            {detail.ai.handover.requested ? (
              <>
                <p className="text-sm text-gray-700 mb-3">{detail.ai.handover.reason}</p>
                <div className="space-y-1 text-xs text-gray-600">
                  <p>{detail.ai.handover.transcript_size} mensagens no pacote transferido</p>
                  {detail.ai.handover.services_consulted.length > 0 && (
                    <p>Sistemas já consultados: {detail.ai.handover.services_consulted.join(', ')}</p>
                  )}
                  {detail.ai.handover.assigned_agent && (
                    <p>Atendente: {detail.ai.handover.assigned_agent}</p>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-700">
                Clara está conduzindo a conversa. A transferência preserva todo o histórico
                e fica disponível a qualquer momento.
              </p>
            )}
          </section>
        </div>
        )}
      </aside>

      <ConversationHistoryModal item={historyItem} onClose={() => setHistoryItem(null)} />
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.author === 'system') {
    return (
      <div className="flex justify-center">
        <div className="flex items-center gap-1.5 px-4 py-2 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
          <Info className="w-3.5 h-3.5" />
          {message.text}
        </div>
      </div>
    );
  }

  const isCustomer = message.author === 'customer';
  const Icon = message.channel ? channelIcons[message.channel] : Globe;
  const AuthorIcon = message.author === 'agent' ? Headset : Bot;

  return (
    <div className={cn('flex', isCustomer ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-lg rounded-2xl px-4 py-3 shadow-sm relative',
        isCustomer ? 'bg-[#E10019] text-white'
          : message.author === 'agent' ? 'bg-emerald-600 text-white'
          : 'bg-white text-gray-900 border border-gray-200')}>
        <p className="text-sm whitespace-pre-wrap">{message.text}</p>
        {isCustomer && message.sentiment && (
          <span className="absolute -left-2.5 -bottom-2">
            <MessageSentimentBadge sentiment={message.sentiment} />
          </span>
        )}
        <div className={cn('flex items-center gap-1.5 mt-1.5 text-xs',
                            isCustomer || message.author === 'agent'
                              ? 'text-white/70' : 'text-gray-400')}>
          {!isCustomer && <AuthorIcon className="w-3 h-3" />}
          <Icon className="w-3 h-3" />
          <span>{new Date(message.timestamp).toLocaleTimeString('pt-BR',
                  { hour: '2-digit', minute: '2-digit' })}</span>
          {message.author === 'agent' && <span>· atendente</span>}
        </div>
      </div>
    </div>
  );
}

function initials(name: string): string {
  return name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase() || '?';
}

function relative(date: Date): string {
  const minutes = Math.floor((Date.now() - date.getTime()) / 60000);
  if (minutes < 1) return 'agora';
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `há ${hours}h` : `há ${Math.floor(hours / 24)}d`;
}
