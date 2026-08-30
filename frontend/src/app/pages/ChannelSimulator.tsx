import { useState } from 'react';
import { Link } from 'react-router';
import {
  MessageCircle, Globe, Smartphone, Phone, Send, Sparkles, ArrowRightLeft,
  UserPlus, Server, Loader2, RotateCcw, ExternalLink,
} from 'lucide-react';

import { api } from '../api/client';
import type { Channel, HubReply } from '../api/types';
import WhatsAppIntegrationPanel from '../components/WhatsAppIntegrationPanel';
import { cn } from '../components/ui/utils';

/**
 * Simulador de Canais — o lado do cliente.
 *
 * O console mostra o hub pela ótica de quem atende. Esta tela mostra pela ótica
 * de quem é atendido: escolha o canal, escreva como o cliente e veja a resposta.
 *
 * O que ela expõe, e que normalmente ficaria invisível, é o *como*: a intenção
 * classificada e a confiança, os sistemas internos acionados, a persona aplicada
 * e — o ponto central da solução — o aviso de que o contexto foi recuperado ao
 * trocar de canal. Trocar o canal no seletor e continuar escrevendo é a
 * demonstração inteira em dois cliques.
 */

const CHANNELS: { id: Channel; label: string; icon: typeof MessageCircle;
                  accent: string; ring: string; bubble: string }[] = [
  { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle,
    accent: 'bg-green-600', ring: 'ring-green-600', bubble: 'bg-green-600' },
  { id: 'web', label: 'Web Chat', icon: Globe,
    accent: 'bg-blue-600', ring: 'ring-blue-600', bubble: 'bg-blue-600' },
  { id: 'app', label: 'App Claro', icon: Smartphone,
    accent: 'bg-[#E10019]', ring: 'ring-[#E10019]', bubble: 'bg-[#E10019]' },
  { id: 'voice', label: 'Voz (URA)', icon: Phone,
    accent: 'bg-purple-600', ring: 'ring-purple-600', bubble: 'bg-purple-600' },
];

const SUGGESTIONS = [
  'Olá, gostaria de alterar meu plano',
  'Quero o Claro Flex 50GB',
  'Minha internet está muito lenta hoje',
  'Preciso da segunda via da minha fatura',
  'Quero falar com um atendente',
];

interface Turn {
  id: number;
  author: 'customer' | 'bot' | 'system';
  text: string;
  channel: Channel;
  meta?: HubReply;
}

export default function ChannelSimulator() {
  const [channel, setChannel] = useState<Channel>('web');
  const [draft, setDraft] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** A identidade do cliente atravessa os canais — é o que o hub usa para lembrar. */
  const [customerId, setCustomerId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lastReply, setLastReply] = useState<HubReply | null>(null);

  const current = CHANNELS.find((c) => c.id === channel)!;

  async function send(text: string) {
    if (!text.trim() || sending) return;
    setSending(true);
    setError(null);

    const mine: Turn = { id: Date.now(), author: 'customer', text, channel };
    setTurns((prev) => [...prev, mine]);
    setDraft('');

    try {
      const reply = await api.sendAsCustomer(channel, {
        text,
        // Na primeira mensagem o hub cria o cliente; a partir daí reusamos o id
        // devolvido. É assim que um canal real amarra a identidade.
        customer_id: customerId ?? undefined,
        external_id: customerId ? undefined : `sim-${Date.now()}`,
      });

      setCustomerId(reply.customer_id);
      setConversationId(reply.conversation_id);
      setLastReply(reply);

      const extra: Turn[] = [];
      if (reply.context_note) {
        extra.push({ id: Date.now() + 1, author: 'system', text: reply.context_note, channel });
      }
      extra.push({ id: Date.now() + 2, author: 'bot', text: reply.reply, channel, meta: reply });
      setTurns((prev) => [...prev, ...extra]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao enviar');
      setTurns((prev) => prev.filter((t) => t.id !== mine.id));
      setDraft(text);
    } finally {
      setSending(false);
    }
  }

  function reset() {
    setTurns([]); setCustomerId(null); setConversationId(null);
    setLastReply(null); setError(null);
  }

  return (
    <div className="h-full flex">
      {/* ---------------------------------------------------- conversa */}
      <div className="flex-1 flex flex-col bg-white min-w-0">
        {/* seletor de canal */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="font-semibold text-gray-900">Simulador de Canais</h2>
              <p className="text-xs text-gray-500">
                Escreva como o cliente. Troque o canal no meio da conversa para ver o hub lembrar.
              </p>
            </div>
            <button
              onClick={reset}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Nova conversa
            </button>
          </div>

          <div className="flex gap-2">
            {CHANNELS.map((c) => {
              const Icon = c.icon;
              const active = c.id === channel;
              return (
                <button
                  key={c.id}
                  onClick={() => setChannel(c.id)}
                  className={cn(
                    'flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border transition-all',
                    active
                      ? `${c.accent} text-white border-transparent shadow-sm`
                      : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50',
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {c.label}
                </button>
              );
            })}
          </div>

          {customerId && (
            <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
              <span className="px-2 py-0.5 bg-gray-100 rounded font-mono">{customerId}</span>
              <span>·</span>
              <span>a identidade atravessa os canais</span>
              {conversationId && (
                <Link
                  to={`/conversation/${conversationId}`}
                  className="ml-auto flex items-center gap-1 text-[#E10019] font-medium hover:underline"
                >
                  Ver no console <ExternalLink className="w-3 h-3" />
                </Link>
              )}
            </div>
          )}
        </div>

        {/* mensagens */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
          {turns.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center px-8">
              <div className={cn('w-14 h-14 rounded-2xl flex items-center justify-center mb-4',
                                 current.accent)}>
                <current.icon className="w-7 h-7 text-white" />
              </div>
              <h3 className="font-medium text-gray-900 mb-1">
                Comece uma conversa pelo {current.label}
              </h3>
              <p className="text-sm text-gray-600 max-w-sm mb-5">
                Depois troque para outro canal e continue escrevendo. O hub retoma de onde parou.
              </p>
              <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="px-3 py-1.5 text-xs bg-white border border-gray-200 rounded-full text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn) => {
            if (turn.author === 'system') {
              return (
                <div key={turn.id} className="flex justify-center">
                  <div className="flex items-center gap-2 px-3.5 py-2 bg-blue-100 text-blue-800 text-xs rounded-full font-medium">
                    <ArrowRightLeft className="w-3.5 h-3.5" />
                    {turn.text}
                  </div>
                </div>
              );
            }

            const isCustomer = turn.author === 'customer';
            const cfg = CHANNELS.find((c) => c.id === turn.channel)!;
            const Icon = cfg.icon;

            return (
              <div key={turn.id} className={cn('flex', isCustomer ? 'justify-end' : 'justify-start')}>
                <div className={cn(
                  'max-w-lg rounded-2xl px-4 py-3 shadow-sm',
                  isCustomer ? `${cfg.bubble} text-white` : 'bg-white text-gray-900 border border-gray-200',
                )}>
                  <p className="text-sm whitespace-pre-wrap">{turn.text}</p>
                  <div className={cn('flex items-center gap-1.5 mt-1.5 text-xs',
                                     isCustomer ? 'text-white/70' : 'text-gray-400')}>
                    <Icon className="w-3 h-3" />
                    <span>{cfg.label}</span>
                    {turn.meta && (
                      <>
                        <span>·</span>
                        <span>{turn.meta.intent.name}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {sending && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-[#E10019]" />
                <span className="text-sm text-gray-500">Clara está respondendo…</span>
              </div>
            </div>
          )}
        </div>

        {/* composer */}
        <div className="p-4 bg-white border-t border-gray-200">
          {error && (
            <p className="mb-2 text-sm text-[#E10019]">{error}</p>
          )}
          <div className="flex items-center gap-3">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send(draft); }}
              placeholder={`Escreva como o cliente no ${current.label}…`}
              disabled={sending}
              className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:border-transparent disabled:opacity-60"
            />
            <button
              onClick={() => send(draft)}
              disabled={sending || !draft.trim()}
              className="p-3 bg-[#E10019] text-white rounded-lg hover:bg-[#C20015] transition-colors disabled:opacity-40"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* ------------------------------------------- o que o hub fez */}
      <aside className="w-96 bg-gradient-to-br from-gray-50 to-white border-l border-gray-200 p-5 overflow-y-auto shrink-0">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">
          Canal real
        </h3>
        <div className="mb-6">
          <WhatsAppIntegrationPanel />
        </div>

        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">
          O que o hub fez
        </h3>

        {!lastReply ? (
          <p className="text-sm text-gray-500">
            Envie uma mensagem para ver a classificação de intenção, os sistemas internos
            acionados e a persona aplicada.
          </p>
        ) : (
          <div className="space-y-4">
            {/* intenção */}
            <section className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-[#E10019]" />
                <h4 className="font-semibold text-gray-900 text-sm">Intenção detectada</h4>
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-mono">
                  RF002
                </span>
              </div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm text-gray-700">{lastReply.intent.name}</span>
                <span className={cn('text-sm font-medium',
                  lastReply.intent.confidence >= 0.75 ? 'text-green-600'
                    : lastReply.intent.confidence >= 0.5 ? 'text-amber-600' : 'text-[#E10019]')}>
                  {Math.round(lastReply.intent.confidence * 100)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5 mb-3">
                <div
                  className={cn('h-1.5 rounded-full',
                    lastReply.intent.confidence >= 0.75 ? 'bg-green-500'
                      : lastReply.intent.confidence >= 0.5 ? 'bg-amber-500' : 'bg-[#E10019]')}
                  style={{ width: `${lastReply.intent.confidence * 100}%` }}
                />
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>motor:</span>
                <span className={cn('px-1.5 py-0.5 rounded font-medium',
                  lastReply.intent.engine.startsWith('llm')
                    ? 'bg-violet-100 text-violet-700' : 'bg-gray-100 text-gray-600')}>
                  {lastReply.intent.engine.startsWith('llm') ? 'LLM' : 'regras'}
                </span>
              </div>
              {Object.keys(lastReply.intent.entities).length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-400 mb-1">Entidades extraídas</p>
                  {Object.entries(lastReply.intent.entities).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-xs">
                      <span className="text-gray-500">{k}</span>
                      <span className="text-gray-900 font-medium">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* contexto */}
            {lastReply.context_recovered && (
              <section className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ArrowRightLeft className="w-4 h-4 text-blue-600" />
                  <h4 className="font-semibold text-gray-900 text-sm">Contexto recuperado</h4>
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-mono">
                    RF003
                  </span>
                </div>
                <p className="text-xs text-gray-700">
                  {lastReply.context_note ?? 'Conversa retomada de onde havia parado.'}
                </p>
              </section>
            )}

            {/* roteamento */}
            <section className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-3">
                <Server className="w-4 h-4 text-gray-500" />
                <h4 className="font-semibold text-gray-900 text-sm">Roteamento</h4>
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-mono">
                  RF004
                </span>
              </div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-500">fluxo</span>
                <span className="text-gray-900 font-medium">{lastReply.flow}</span>
              </div>
              <p className="text-xs text-gray-400 mb-1.5">Sistemas internos consultados</p>
              {lastReply.services_consulted.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {lastReply.services_consulted.map((s) => (
                    <span key={s} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-mono">
                      {s}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400">nenhum</p>
              )}
            </section>

            {/* persona */}
            <section className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-2">
                <h4 className="font-semibold text-gray-900 text-sm">Persona aplicada</h4>
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-mono">
                  RF006
                </span>
              </div>
              <p className="text-xs text-gray-700">{lastReply.persona_applied}</p>
              <Link to="/design-studio"
                className="mt-2 inline-block text-xs text-[#E10019] font-medium hover:underline">
                Alterar no Design Studio →
              </Link>
            </section>

            {/* handover */}
            {lastReply.handover_triggered && (
              <section className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <UserPlus className="w-4 h-4 text-amber-600" />
                  <h4 className="font-semibold text-gray-900 text-sm">Transferido para humano</h4>
                  <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-mono">
                    RF005
                  </span>
                </div>
                <p className="text-xs text-gray-700 mb-2">{lastReply.handover_reason}</p>
                <Link to="/inbox"
                  className="text-xs text-[#E10019] font-medium hover:underline">
                  A conversa está na fila do Inbox →
                </Link>
              </section>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
