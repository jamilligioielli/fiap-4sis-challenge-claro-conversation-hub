import type { Sentiment } from '../../api/types';
import { SENTIMENT_STYLES } from '../../lib/sentiment';
import { cn } from '../ui/utils';

/**
 * Humor atual do cliente, no topo do painel do atendente.
 *
 * Vem antes de tudo porque muda a forma de abrir a conversa: um cliente
 * frustrado precisa ser ouvido antes de receber qualquer oferta.
 */
export default function SentimentIndicator({ sentiment, score }: {
  sentiment: Sentiment | null | undefined; score?: number | null;
}) {
  if (!sentiment) {
    return (
      <div className="rounded-xl border border-dashed border-gray-200 bg-white p-3 text-xs text-gray-500">
        Humor do cliente ainda não detectado — aparece a partir da primeira mensagem.
      </div>
    );
  }
  const style = SENTIMENT_STYLES[sentiment];
  const index = score == null ? null : Math.round(score * 100);

  return (
    <div role="status" aria-live="polite"
         aria-label={`Sentimento do cliente: ${style.label}`}
         className={cn('rounded-xl border p-3 flex items-start gap-3', style.banner)}>
      <span className="text-3xl leading-none" aria-hidden>{style.emoji}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-bold uppercase tracking-wide">{style.label}</p>
          {index != null && (
            <span className="text-[11px] font-medium opacity-80"
                  title="Índice de humor: 0 insatisfeito, 50 neutro, 100 satisfeito">
              índice {index}/100
            </span>
          )}
        </div>
        <p className="text-xs mt-0.5 leading-snug">
          {sentiment === 'negative' && <span aria-hidden>⚠️ </span>}
          {style.guidance}
        </p>
      </div>
    </div>
  );
}
