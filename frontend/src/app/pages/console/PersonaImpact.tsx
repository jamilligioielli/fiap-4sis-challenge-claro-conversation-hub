import { useState } from 'react';
import { Link } from 'react-router';
import {
  Wand2, Loader2, MessageCircle, Globe, Smartphone, Phone, ArrowRight,
  AlertTriangle, Ruler, Smile, MessageSquareText,
} from 'lucide-react';

import { api } from '../../api/client';
import { useCustomers } from '../../api/hooks';
import type { PersonaPreview } from '../../api/types';
import { cn } from '../../components/ui/utils';

/**
 * O efeito da configuração, dentro da conversa.
 *
 * Uma tela de configuração que não mostra consequência pede um ato de fé: mudei
 * o tom, e agora? Este painel fecha o laço de duas formas — mostrando a mesma
 * frase reescrita por canal com a configuração vigente, e levando de volta a uma
 * conversa já simulada, onde a próxima resposta do assistente pode ser conferida
 * contra a versão da persona que a produziu.
 */

const ICONS: Record<string, typeof MessageCircle> = {
  whatsapp: MessageCircle, webchat: Globe, web: Globe, app: Smartphone, voice: Phone,
};

const DEFAULT_MESSAGE =
  'Vi que você quer alterar seu plano. Posso te ajudar com isso agora mesmo.';

export default function PersonaImpact({ version }: { version: number }) {
  const customersState = useCustomers();
  const [message, setMessage] = useState(DEFAULT_MESSAGE);
  const [preview, setPreview] = useState<PersonaPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!message.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      setPreview(await api.previewPersona(message.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao gerar a prévia');
    } finally {
      setLoading(false);
    }
  }

  const withHistory = (customersState.data ?? []).filter((c) => c.conversation_count > 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-full bg-violet-50 flex items-center justify-center">
          <Wand2 className="w-5 h-5 text-violet-600" />
        </div>
        <h2 className="text-lg font-semibold text-gray-900">O que muda na conversa</h2>
        <span className="ml-auto text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600 font-mono">
          persona v{version}
        </span>
      </div>
      <p className="text-sm text-gray-600 mb-5 max-w-3xl">
        Configuração sem consequência visível é ato de fé. Escreva uma frase e veja como
        ela sai em cada canal com o que está salvo agora — e depois volte a uma conversa
        já simulada para conferir na prática.
      </p>

      {/* ---------------------------------------- mesma frase, cada canal */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void run(); }}
          placeholder="Escreva o que o assistente diria…"
          className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white transition"
        />
        <button
          onClick={() => void run()}
          disabled={loading || !message.trim()}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-[#E10019] text-white rounded-lg text-sm font-medium hover:bg-[#C20015] transition-colors disabled:opacity-40"
        >
          {loading
            ? <><Loader2 className="w-4 h-4 animate-spin" /> gerando…</>
            : <><Wand2 className="w-4 h-4" /> Ver o efeito</>}
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-[#E10019]">{error}</p>}

      {preview && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
          {preview.previews.map((channel) => {
            const Icon = ICONS[channel.channel_id] ?? MessageSquareText;
            const overflow = channel.length > channel.max_length;
            return (
              <div
                key={channel.channel_id}
                className="p-4 border border-gray-200 rounded-xl bg-gray-50/60"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-900">
                    {channel.channel_name}
                  </span>
                </div>
                <p className="text-sm text-gray-800 leading-relaxed mb-3">
                  {channel.rendered}
                </p>
                <div className="flex items-center gap-2 flex-wrap text-[11px]">
                  <span className="px-1.5 py-0.5 bg-white border border-gray-200 rounded text-gray-600">
                    {channel.formality_label}
                  </span>
                  <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded border',
                    channel.use_emoji
                      ? 'bg-amber-50 border-amber-200 text-amber-700'
                      : 'bg-white border-gray-200 text-gray-500')}>
                    <Smile className="w-3 h-3" />
                    {channel.use_emoji ? 'emojis' : 'sem emoji'}
                  </span>
                  <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded border',
                    overflow
                      ? 'bg-red-50 border-red-200 text-[#E10019] font-medium'
                      : 'bg-white border-gray-200 text-gray-500')}>
                    {overflow ? <AlertTriangle className="w-3 h-3" /> : <Ruler className="w-3 h-3" />}
                    {channel.length}/{channel.max_length}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ------------------------------- conferir dentro de uma conversa real */}
      <div className="pt-5 border-t border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900 mb-1">
          Conferir numa conversa já simulada
        </h3>
        <p className="text-xs text-gray-600 mb-3 max-w-3xl">
          A prévia acima é uma amostra. A verificação de verdade é mandar outra mensagem
          numa conversa que já existe: cada resposta do assistente carrega a versão da
          persona que a produziu, então dá para ver a resposta anterior com a versão
          antiga e a nova com a <span className="font-mono">v{version}</span>, lado a lado
          na mesma tela.
        </p>

        {withHistory.length === 0 ? (
          <p className="text-xs text-gray-500">
            Nenhuma conversa simulada ainda.{' '}
            <Link to="/simulador" className="text-[#E10019] font-medium hover:underline">
              Comece uma pelo simulador
            </Link>{' '}
            e volte aqui.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {withHistory.map((customer) => (
              <Link
                key={customer.id}
                to={`/simulador/${customer.id}`}
                className="group flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-700 hover:border-[#E10019] hover:text-[#E10019] transition-colors"
              >
                {customer.name}
                <span className="text-gray-400 font-normal">
                  {customer.conversation_count} conversa{customer.conversation_count > 1 ? 's' : ''}
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-[#E10019]" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
