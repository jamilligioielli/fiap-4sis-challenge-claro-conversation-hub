import type { Sentiment } from '../../api/types';
import { SENTIMENT_STYLES } from '../../lib/sentiment';

/** Emoji discreto ao lado de cada mensagem do cliente, com o humor no tooltip. */
export default function MessageSentimentBadge({ sentiment }: { sentiment: Sentiment }) {
  const style = SENTIMENT_STYLES[sentiment];
  const text = `Sentimento detectado: ${style.description}`;
  return (
    <span
      title={text}
      aria-label={text}
      role="img"
      className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-white/90 text-[11px] leading-none shadow-sm"
    >
      {style.emoji}
    </span>
  );
}
