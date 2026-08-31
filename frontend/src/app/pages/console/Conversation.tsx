import { useState } from 'react';
import { Link, useParams } from 'react-router';
import {
  Globe, MessageCircle, Smartphone, Phone, ArrowRight, User, Sparkles, Send,
  UserPlus, ChevronRight, Loader2, Bot, Headset, Info,
} from 'lucide-react';

import { api } from '../../api/client';
import { useConversation } from '../../api/hooks';
import type { Channel, ConversationDetail, Message } from '../../api/types';
import { AsyncBoundary } from '../../components/AsyncBoundary';
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

  const startedAt = new Date(detail.started_at);
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

  async function handover() {
    setBusy(true); setError(null);
    try {
      await api.requestHandover(detail.id, 'Assumido pelo atendente no console', 'Admin CX');
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao transferir');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="h-full flex">
      {/* ------------------------------------------------ transcrição */}
      <div className="flex-1 flex flex-col bg-white min-w-0">
        <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-[#E10019] flex items-center justify-center text-white font-semibold">
                {initials(detail.customer_name)}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">{detail.customer_name}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-600">
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
          <div className="flex items-center gap-3 mt-3">
            <button
              onClick={handover}
              disabled={busy || detail.status === 'transferred'}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium flex items-center gap-2 disabled:opacity-40"
            >
              <UserPlus className="w-4 h-4" />
              {detail.status === 'transferred' ? 'Já transferida' : 'Assumir como humano'}
            </button>
            <span className="text-xs text-gray-500">
              A resposta sai pelo último canal usado pelo cliente
              {detail.channels_used.length > 0 &&
                ` (${channelLabels[detail.channels_used[detail.channels_used.length - 1]]})`}
            </span>
          </div>
        </div>
      </div>

      {/* -------------------------------------------------- painel de IA */}
      <aside className="w-96 bg-gradient-to-br from-gray-50 to-white border-l border-gray-200 p-6 overflow-y-auto shrink-0">
        <div className="space-y-6">
          {detail.ai.intent && (
            <section className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-[#E10019]" />
                <h4 className="font-semibold text-gray-900">Intenção Detectada</h4>
              </div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">{detail.ai.intent.name}</span>
                <span className={cn('text-sm font-medium',
                  detail.ai.intent.confidence >= 0.75 ? 'text-green-600'
                    : detail.ai.intent.confidence >= 0.5 ? 'text-amber-600' : 'text-[#E10019]')}>
                  {Math.round(detail.ai.intent.confidence * 100)}% confiança
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={cn('h-2 rounded-full',
                    detail.ai.intent.confidence >= 0.75 ? 'bg-green-500'
                      : detail.ai.intent.confidence >= 0.5 ? 'bg-amber-500' : 'bg-[#E10019]')}
                  style={{ width: `${detail.ai.intent.confidence * 100}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-gray-400">
                motor: {detail.ai.intent.engine.startsWith('llm') ? 'LLM' : 'regras'}
              </p>
            </section>
          )}

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
      </aside>
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
      <div className={cn('max-w-lg rounded-2xl px-4 py-3 shadow-sm',
        isCustomer ? 'bg-[#E10019] text-white'
          : message.author === 'agent' ? 'bg-emerald-600 text-white'
          : 'bg-white text-gray-900 border border-gray-200')}>
        <p className="text-sm whitespace-pre-wrap">{message.text}</p>
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
