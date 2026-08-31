import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import {
  MessageCircle, Globe, Smartphone, Phone, Send, Sparkles, ArrowRightLeft,
  UserPlus, Server, Loader2, ArrowLeft, ExternalLink, PenLine, FileText,
  History, Check, X, Info, Megaphone, Wand2,
} from 'lucide-react';

import { api } from '../../api/client';
import { useCustomerContext, useCustomerConversations } from '../../api/hooks';
import type {
  Channel, ConversationListItem, CustomerContext as CustomerCtx, HubReply,
  Message, ResponseSource,
} from '../../api/types';
import { ErrorState, Loading } from '../../components/AsyncBoundary';
import { cn } from '../../components/ui/utils';

/**
 * O lado do cliente — já sabendo quem ele é.
 *
 * A tela anterior escolheu a persona, então aqui não existe "cliente não
 * identificado": o assistente cumprimenta pelo nome, conhece o plano e o
 * histórico, e tudo o que for dito fica salvo no contexto desse cliente.
 *
 * A demonstração central acontece no seletor de canal: começar no WhatsApp,
 * trocar para o App e continuar escrevendo. O hub não presume que o assunto é o
 * mesmo — ele reconhece a conversa anterior e pergunta antes de seguir.
 */

interface ChannelSkin {
  id: Channel;
  label: string;
  icon: typeof MessageCircle;
  accent: string;
  bubble: string;
  surface: string;
}

const SKINS: ChannelSkin[] = [
  { id: 'whatsapp', label: 'WhatsApp', icon: MessageCircle,
    accent: 'bg-[#25D366]', bubble: 'bg-[#25D366]', surface: 'bg-[#ECE5DD]' },
  { id: 'web', label: 'Web Chat', icon: Globe,
    accent: 'bg-blue-600', bubble: 'bg-blue-600', surface: 'bg-slate-100' },
  { id: 'app', label: 'App Claro', icon: Smartphone,
    accent: 'bg-[#E10019]', bubble: 'bg-[#E10019]', surface: 'bg-rose-50/60' },
];

const skin = (id: Channel | null): ChannelSkin => SKINS.find((s) => s.id === id) ?? SKINS[1];

const SUGGESTIONS = [
  'Quero aumentar minha franquia de internet',
  'Minha internet está muito lenta hoje',
  'Preciso da segunda via da minha fatura',
  'Quanto ficaria um plano com mais dados?',
  'Quero falar com um atendente',
];

interface Bubble {
  key: string;
  author: 'customer' | 'bot' | 'agent' | 'system';
  text: string;
  channel: Channel | null;
  source?: ResponseSource | null;
  intent?: string | null;
}

function toBubble(message: Message): Bubble {
  return {
    key: message.id,
    author: message.author === 'system' ? 'system' : message.author,
    text: message.text,
    channel: message.channel,
    source: message.source,
    intent: message.intent?.name ?? null,
  };
}

export default function SimulatorChat() {
  const { customerId } = useParams<{ customerId: string }>();
  const customerState = useCustomerContext(customerId);
  const historyState = useCustomerConversations(customerId);

  const [channel, setChannel] = useState<Channel>('whatsapp');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [draft, setDraft] = useState('');
  const [booting, setBooting] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastReply, setLastReply] = useState<HubReply | null>(null);
  const [personaApplied, setPersonaApplied] = useState<string | null>(null);
  const [personaVersion, setPersonaVersion] = useState<number | null>(null);
  const [greetingSource, setGreetingSource] = useState<ResponseSource | null>(null);
  const [replayed, setReplayed] = useState<string | null>(null);
  const [showVoice, setShowVoice] = useState(false);

  const bottom = useRef<HTMLDivElement>(null);
  const customer = customerState.data;
  const current = skin(channel);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [bubbles, sending]);

  /** Abre (ou retoma) a conversa deste cliente e traz o que já foi dito. */
  const boot = useCallback(async (target: Channel) => {
    if (!customerId) return;
    setBooting(true);
    setError(null);
    try {
      const started = await api.startConversation(customerId, target);
      setConversationId(started.conversation_id);
      setPersonaApplied(started.persona_applied);
      setPersonaVersion(started.persona_version);
      setGreetingSource(started.response_source);

      if (started.resumed) {
        // Conversa em andamento: o histórico é a fonte da verdade, não a memória
        // desta aba. Quem volta ao simulador reencontra exatamente onde parou.
        const detail = await api.getConversation(started.conversation_id);
        setBubbles(detail.messages.map(toBubble));
      } else {
        setBubbles([{
          key: `greeting-${started.conversation_id}`,
          author: 'bot',
          text: started.greeting,
          channel: target,
          source: started.response_source,
        }]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao abrir a conversa');
    } finally {
      setBooting(false);
    }
  }, [customerId]);

  useEffect(() => {
    if (!customerId) return;
    setBubbles([]);
    setLastReply(null);
    setReplayed(null);
    void boot('whatsapp');
    setChannel('whatsapp');
  }, [customerId, boot]);

  function switchChannel(next: Channel) {
    if (next === channel || sending) return;
    setChannel(next);
    setShowVoice(false);
    setBubbles((prev) => [...prev, {
      key: `switch-${next}-${Date.now()}`,
      author: 'system',
      text: `Você abriu o ${skin(next).label}. Escreva para continuar.`,
      channel: next,
    }]);
  }

  async function send(text: string) {
    const clean = text.trim();
    if (!clean || sending || !customerId) return;

    setSending(true);
    setError(null);
    setDraft('');
    const mineKey = `mine-${Date.now()}`;
    setBubbles((prev) => [...prev, {
      key: mineKey, author: 'customer', text: clean, channel,
    }]);

    try {
      const reply = await api.sendAsCustomer(channel, { text: clean, customer_id: customerId });
      setConversationId(reply.conversation_id);
      setLastReply(reply);
      setPersonaApplied(reply.persona_applied);
      setPersonaVersion(reply.persona_version);

      setBubbles((prev) => [...prev, {
        key: `bot-${reply.conversation_id}-${prev.length}`,
        author: 'bot',
        text: reply.reply,
        channel,
        source: reply.response_source,
        intent: reply.intent.name,
      }]);
      historyState.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao enviar');
      setBubbles((prev) => prev.filter((b) => b.key !== mineKey));
      setDraft(clean);
    } finally {
      setSending(false);
    }
  }

  /** Traz uma conversa anterior deste cliente de volta para a tela. */
  async function replay(conversation: ConversationListItem) {
    setError(null);
    setReplayed(conversation.id);
    try {
      const detail = await api.getConversation(conversation.id);
      setBubbles(detail.messages.map(toBubble));
      setConversationId(conversation.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao carregar a conversa');
      setReplayed(null);
    }
  }

  if (!customerId) return <ErrorState message="Nenhum cliente selecionado." />;
  if (customerState.loading && !customer) return <Loading label="Carregando o cliente…" />;
  if (customerState.error && !customer) {
    return <ErrorState message={customerState.error} onRetry={customerState.reload} />;
  }

  const awaiting = lastReply?.awaiting_context_confirmation ?? false;
  const readOnly = replayed !== null && replayed !== conversationId;

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <SimulatorHeader customer={customer} />

      <div className="flex-1 flex min-h-0">
        {/* ------------------------------------------------------- conversa */}
        <div className="flex-1 flex flex-col min-w-0 bg-white">
          <ChannelBar
            channel={channel}
            disabled={sending || booting}
            onSwitch={switchChannel}
            onVoice={() => setShowVoice((v) => !v)}
            voiceOpen={showVoice}
          />

          {showVoice && <VoiceNotice onClose={() => setShowVoice(false)} />}

          <div className={cn('flex-1 overflow-y-auto p-5 space-y-3', current.surface)}>
            {booting ? (
              <div className="h-full flex items-center justify-center">
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="w-4 h-4 animate-spin text-[#E10019]" />
                  Abrindo a conversa…
                </div>
              </div>
            ) : (
              <>
                {bubbles.map((bubble) => (
                  <BubbleRow key={bubble.key} bubble={bubble} />
                ))}

                {sending && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 flex items-center gap-2 shadow-sm">
                      <Loader2 className="w-4 h-4 animate-spin text-[#E10019]" />
                      <span className="text-sm text-gray-500">escrevendo…</span>
                    </div>
                  </div>
                )}

                <div ref={bottom} />
              </>
            )}
          </div>

          {/* respostas rápidas para a pergunta de continuidade */}
          {awaiting && !sending && (
            <div className="px-5 py-3 bg-blue-50 border-t border-blue-200">
              <p className="text-xs text-blue-900 mb-2 font-medium">
                O assistente está esperando você decidir sobre o assunto anterior.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => send('Sim, quero continuar nesse assunto')}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-blue-300 text-blue-800 rounded-full text-xs font-medium hover:bg-blue-100 transition-colors"
                >
                  <Check className="w-3.5 h-3.5" />
                  Continuar nesse assunto
                </button>
                <button
                  onClick={() => send('Não, é outro assunto')}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 text-gray-700 rounded-full text-xs font-medium hover:bg-gray-100 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                  É outro assunto
                </button>
              </div>
            </div>
          )}

          {/* sugestões só antes da primeira mensagem do cliente */}
          {!booting && !awaiting && !bubbles.some((b) => b.author === 'customer') && (
            <div className="px-5 py-3 border-t border-gray-100 bg-white">
              <p className="text-xs text-gray-400 mb-2">Sugestões para começar</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="px-3 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-full text-gray-700 hover:border-gray-300 hover:bg-gray-100 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="p-4 bg-white border-t border-gray-200">
            {error && <p className="mb-2 text-sm text-[#E10019]">{error}</p>}
            {readOnly && (
              <p className="mb-2 flex items-center gap-1.5 text-xs text-gray-500">
                <History className="w-3.5 h-3.5" />
                Você está vendo uma conversa anterior. Escrever aqui continua na conversa atual.
                <button
                  onClick={() => { setReplayed(null); void boot(channel); }}
                  className="text-[#E10019] font-medium hover:underline"
                >
                  voltar
                </button>
              </p>
            )}
            <div className="flex items-center gap-3">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void send(draft); }}
                placeholder={`Escreva como ${customer?.name.split(' ')[0] ?? 'o cliente'} no ${current.label}…`}
                disabled={sending || booting}
                className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:border-transparent disabled:opacity-60"
              />
              <button
                onClick={() => void send(draft)}
                disabled={sending || booting || !draft.trim()}
                aria-label="Enviar mensagem"
                className="p-3 bg-[#E10019] text-white rounded-lg hover:bg-[#C20015] transition-colors disabled:opacity-40"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------- o que o hub fez */}
        <aside className="w-[22rem] bg-gradient-to-b from-gray-50 to-white border-l border-gray-200 p-5 overflow-y-auto shrink-0">
          <HubPanel
            reply={lastReply}
            personaApplied={personaApplied}
            personaVersion={personaVersion}
            greetingSource={greetingSource}
            conversationId={conversationId}
          />

          <PastConversations
            state={historyState}
            activeId={conversationId}
            onReplay={replay}
          />
        </aside>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ cabeçalho
function SimulatorHeader({ customer }: { customer: CustomerCtx | null }) {
  const initials = customer?.name.split(' ').slice(0, 2).map((p) => p[0]).join('') ?? '··';

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4 shrink-0">
      <Link
        to="/simulador"
        className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Trocar de cliente
      </Link>

      <div className="w-px h-8 bg-gray-200" />

      <div className="w-10 h-10 rounded-full bg-[#E10019] flex items-center justify-center text-white text-sm font-semibold shrink-0">
        {initials}
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="font-semibold text-gray-900 truncate">
            {customer?.name ?? 'Carregando…'}
          </h1>
          {customer?.segment && (
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
              {customer.segment}
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 truncate">
          {customer?.plan
            ? `${customer.plan.name} · ${customer.plan.usage_percent}% da franquia · cliente desde ${customer.customer_since}`
            : 'sem plano ativo'}
        </p>
      </div>

      <Link
        to="/console"
        className="ml-auto flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-gray-900"
      >
        Ver como a Claro
        <ExternalLink className="w-3.5 h-3.5" />
      </Link>
    </header>
  );
}

// -------------------------------------------------------------- barra de canal
function ChannelBar({ channel, disabled, onSwitch, onVoice, voiceOpen }: {
  channel: Channel;
  disabled: boolean;
  onSwitch: (next: Channel) => void;
  onVoice: () => void;
  voiceOpen: boolean;
}) {
  return (
    <div className="px-5 py-3 border-b border-gray-200 flex items-center gap-2 flex-wrap">
      {SKINS.map((s) => {
        const Icon = s.icon;
        const active = s.id === channel;
        return (
          <button
            key={s.id}
            onClick={() => onSwitch(s.id)}
            disabled={disabled}
            className={cn(
              'flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border transition-all disabled:opacity-50',
              active
                ? `${s.accent} text-white border-transparent shadow-sm`
                : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50',
            )}
          >
            <Icon className="w-4 h-4" />
            {s.label}
          </button>
        );
      })}

      {/* O canal de voz é por ligação — simular por escrito daria uma impressão
          falsa do que ele é. Fica como o que realmente é: um telefone. */}
      <button
        onClick={onVoice}
        className={cn(
          'flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium border border-dashed transition-all',
          voiceOpen
            ? 'border-purple-400 bg-purple-50 text-purple-700'
            : 'border-gray-300 text-gray-500 hover:bg-gray-50',
        )}
      >
        <Phone className="w-4 h-4" />
        Ligar para a Claro
      </button>

      <span className="ml-auto text-xs text-gray-400 hidden lg:block">
        troque de canal no meio da conversa
      </span>
    </div>
  );
}

function VoiceNotice({ onClose }: { onClose: () => void }) {
  return (
    <div className="px-5 py-4 bg-purple-50 border-b border-purple-200 flex items-start gap-3">
      <Phone className="w-5 h-5 text-purple-600 mt-0.5 shrink-0" />
      <div className="flex-1 text-sm text-purple-900">
        <p className="font-medium mb-1">O canal de voz atende por ligação — 1052.</p>
        <p className="text-purple-800/90 leading-relaxed">
          A URA já é um canal do hub: a configuração de voz, o roteiro e os gatilhos de
          transferência estão no Design Studio, e uma ligação entra pelo mesmo endpoint de
          ingestão dos outros canais. O que ainda não existe é a simulação de áudio por aqui —
          fica para a próxima versão do projeto.
        </p>
      </div>
      <button onClick={onClose} className="text-purple-400 hover:text-purple-700">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

// -------------------------------------------------------------------- balões
function BubbleRow({ bubble }: { bubble: Bubble }) {
  if (bubble.author === 'system') {
    return (
      <div className="flex justify-center">
        <div className="flex items-center gap-2 px-3.5 py-1.5 bg-white/80 backdrop-blur text-gray-600 text-xs rounded-full border border-gray-200">
          <ArrowRightLeft className="w-3 h-3" />
          {bubble.text}
        </div>
      </div>
    );
  }

  const isCustomer = bubble.author === 'customer';
  const cfg = skin(bubble.channel);
  const Icon = cfg.icon;

  return (
    <div className={cn('flex', isCustomer ? 'justify-end' : 'justify-start')}>
      <div className={cn(
        'max-w-lg rounded-2xl px-4 py-3 shadow-sm',
        isCustomer
          ? `${cfg.bubble} text-white`
          : bubble.author === 'agent'
            ? 'bg-amber-50 text-gray-900 border border-amber-200'
            : 'bg-white text-gray-900 border border-gray-200',
      )}>
        {bubble.author === 'agent' && (
          <p className="text-[11px] font-semibold text-amber-700 mb-1 flex items-center gap-1">
            <UserPlus className="w-3 h-3" />
            atendente humano
          </p>
        )}
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{bubble.text}</p>
        <div className={cn('flex items-center gap-1.5 mt-1.5 text-[11px]',
                           isCustomer ? 'text-white/70' : 'text-gray-400')}>
          <Icon className="w-3 h-3" />
          <span>{cfg.label}</span>
          {bubble.source && (
            <>
              <span>·</span>
              <span className="flex items-center gap-1">
                {bubble.source === 'generative'
                  ? <><Wand2 className="w-3 h-3" /> escrito por IA</>
                  : <><FileText className="w-3 h-3" /> modelo de texto</>}
              </span>
            </>
          )}
          {bubble.intent && !isCustomer && (
            <>
              <span>·</span>
              <span>{bubble.intent}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------- painel lateral
function HubPanel({ reply, personaApplied, personaVersion, greetingSource, conversationId }: {
  reply: HubReply | null;
  personaApplied: string | null;
  personaVersion: number | null;
  greetingSource: ResponseSource | null;
  conversationId: string | null;
}) {
  const source = reply?.response_source ?? greetingSource;

  return (
    <>
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
        O que o hub fez
      </h3>

      {/* quem escreveu a resposta — a pergunta que a solução precisa responder */}
      <section className={cn(
        'rounded-xl border p-4 mb-4',
        source === 'generative'
          ? 'bg-violet-50 border-violet-200'
          : 'bg-white border-gray-200',
      )}>
        <div className="flex items-center gap-2 mb-2">
          {source === 'generative'
            ? <Wand2 className="w-4 h-4 text-violet-600" />
            : <PenLine className="w-4 h-4 text-gray-500" />}
          <h4 className="font-semibold text-gray-900 text-sm">Quem escreveu a resposta</h4>
        </div>
        <p className="text-xs text-gray-700 leading-relaxed">
          {source === 'generative'
            ? 'Redigida na hora por um modelo de linguagem, considerando a persona, o '
              + 'perfil do cliente e tudo o que já foi dito nesta conversa.'
            : 'Escrita a partir de modelos de texto. Configure uma chave de modelo de '
              + 'linguagem para ver a redação generativa.'}
        </p>
        {reply?.response_model && (
          <p className="mt-2 text-[11px] text-gray-500 font-mono">{reply.response_model}</p>
        )}
      </section>

      {!reply ? (
        <p className="text-sm text-gray-500 mb-6">
          Escreva a primeira mensagem para ver a intenção classificada, os sistemas
          internos consultados e a persona aplicada.
        </p>
      ) : (
        <div className="space-y-4 mb-6">
          {/* pergunta de continuidade */}
          {reply.awaiting_context_confirmation && (
            <section className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <ArrowRightLeft className="w-4 h-4 text-blue-600" />
                <h4 className="font-semibold text-gray-900 text-sm">Aguardando o cliente decidir</h4>
              </div>
              <p className="text-xs text-gray-700 leading-relaxed">
                O cliente mudou de canal com assunto em aberto. O hub reconheceu a conversa
                anterior e perguntou antes de agir — decidir pelo cliente é o mesmo erro que
                a solução existe para corrigir, só que ao contrário.
              </p>
            </section>
          )}

          {reply.context_recovered && !reply.awaiting_context_confirmation && (
            <section className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <ArrowRightLeft className="w-4 h-4 text-emerald-600" />
                <h4 className="font-semibold text-gray-900 text-sm">Contexto recuperado</h4>
              </div>
              <p className="text-xs text-gray-700">
                {reply.context_note ?? 'Conversa retomada de onde havia parado.'}
              </p>
            </section>
          )}

          {/* intenção */}
          <section className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-[#E10019]" />
              <h4 className="font-semibold text-gray-900 text-sm">Intenção detectada</h4>
            </div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm text-gray-700">{reply.intent.name}</span>
              <span className={cn('text-sm font-medium',
                reply.intent.confidence >= 0.75 ? 'text-green-600'
                  : reply.intent.confidence >= 0.5 ? 'text-amber-600' : 'text-[#E10019]')}>
                {Math.round(reply.intent.confidence * 100)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5 mb-3">
              <div
                className={cn('h-1.5 rounded-full',
                  reply.intent.confidence >= 0.75 ? 'bg-green-500'
                    : reply.intent.confidence >= 0.5 ? 'bg-amber-500' : 'bg-[#E10019]')}
                style={{ width: `${reply.intent.confidence * 100}%` }}
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>motor:</span>
              <span className={cn('px-1.5 py-0.5 rounded font-medium',
                reply.intent.engine.startsWith('llm')
                  ? 'bg-violet-100 text-violet-700' : 'bg-gray-100 text-gray-600')}>
                {reply.intent.engine.startsWith('llm') ? 'modelo de linguagem' : 'regras'}
              </span>
            </div>
            {Object.keys(reply.intent.entities).length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-400 mb-1">Entidades extraídas</p>
                {Object.entries(reply.intent.entities).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-gray-500">{k}</span>
                    <span className="text-gray-900 font-medium">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* roteamento */}
          <section className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Server className="w-4 h-4 text-gray-500" />
              <h4 className="font-semibold text-gray-900 text-sm">Roteamento</h4>
            </div>
            <div className="flex justify-between text-xs mb-2">
              <span className="text-gray-500">fluxo</span>
              <span className="text-gray-900 font-medium">{reply.flow}</span>
            </div>
            <p className="text-xs text-gray-400 mb-1.5">Sistemas internos consultados</p>
            {reply.services_consulted.length ? (
              <div className="flex flex-wrap gap-1.5">
                {reply.services_consulted.map((s) => (
                  <span key={s} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-mono">
                    {s}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400">nenhum</p>
            )}
          </section>

          {reply.handover_triggered && (
            <section className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <UserPlus className="w-4 h-4 text-amber-600" />
                <h4 className="font-semibold text-gray-900 text-sm">Transferido para humano</h4>
              </div>
              <p className="text-xs text-gray-700 mb-2">{reply.handover_reason}</p>
              <Link to="/console/inbox" className="text-xs text-[#E10019] font-medium hover:underline">
                A conversa está na fila do console →
              </Link>
            </section>
          )}
        </div>
      )}

      {/* persona — sempre visível, porque é o que o Design Studio controla */}
      {personaApplied && (
        <section className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <h4 className="font-semibold text-gray-900 text-sm">Persona aplicada</h4>
            {personaVersion != null && (
              <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-mono">
                v{personaVersion}
              </span>
            )}
          </div>
          <p className="text-xs text-gray-700 leading-relaxed">{personaApplied}</p>
          <Link
            to="/console/design-studio"
            className="mt-2 inline-block text-xs text-[#E10019] font-medium hover:underline"
          >
            Mudar o tom no Design Studio →
          </Link>
        </section>
      )}

      {conversationId && (
        <Link
          to={`/console/conversation/${conversationId}`}
          className="flex items-center justify-center gap-1.5 w-full px-3 py-2 mb-6 border border-gray-200 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Abrir esta conversa no console
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      )}
    </>
  );
}

// -------------------------------------------------- conversas deste cliente
function PastConversations({ state, activeId, onReplay }: {
  state: { data: ConversationListItem[] | null; loading: boolean };
  activeId: string | null;
  onReplay: (conversation: ConversationListItem) => void;
}) {
  const conversations = state.data ?? [];

  return (
    <section>
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
        Conversas deste cliente
      </h3>

      {conversations.length === 0 ? (
        <p className="flex items-start gap-2 text-xs text-gray-500">
          <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          Nenhuma ainda. O que for dito aqui fica salvo no contexto deste cliente e volta
          a aparecer quando ele retornar — por qualquer canal.
        </p>
      ) : (
        <div className="space-y-2">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              onClick={() => onReplay(conversation)}
              className={cn(
                'w-full text-left p-3 rounded-lg border transition-colors',
                conversation.id === activeId
                  ? 'border-[#E10019] bg-red-50/50'
                  : 'border-gray-200 bg-white hover:bg-gray-50',
              )}
            >
              <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                {conversation.channels_used.map((c) => {
                  const Icon = skin(c).icon;
                  return <Icon key={c} className="w-3 h-3 text-gray-400" />;
                })}
                <span className="text-xs font-medium text-gray-900">
                  {conversation.intent ?? conversation.area}
                </span>
                {conversation.initiated_by_company && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-medium">
                    <Megaphone className="w-2.5 h-2.5" />
                    a Claro iniciou
                  </span>
                )}
                {conversation.id === activeId && (
                  <span className="ml-auto text-[10px] text-[#E10019] font-medium">atual</span>
                )}
              </div>
              <p className="text-xs text-gray-600 line-clamp-2">{conversation.last_message}</p>
              <p className="text-[11px] text-gray-400 mt-1">
                {conversation.message_count} mensagens · {conversation.timestamp}
              </p>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
