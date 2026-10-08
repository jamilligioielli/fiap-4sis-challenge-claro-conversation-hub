import type { Sentiment } from '../api/types';

/**
 * Como cada humor aparece para o atendente.
 *
 * Emoji, rótulo e cor andam juntos: a cor sozinha não chega a quem não
 * distingue vermelho de verde, e o emoji sozinho não chega a leitor de tela.
 */
export interface SentimentStyle {
  emoji: string;
  label: string;
  description: string;
  guidance: string;
  /** Fundo, borda e texto do banner. */
  banner: string;
  /** Selo pequeno. */
  pill: string;
}

export const SENTIMENT_STYLES: Record<Sentiment, SentimentStyle> = {
  positive: {
    emoji: '😊',
    label: 'Calmo',
    description: 'positivo',
    guidance: 'Cliente satisfeito — bom momento para seguir com a oferta.',
    banner: 'bg-green-50 border-green-200 text-green-900',
    pill: 'bg-green-50 text-green-800 border-green-200',
  },
  neutral: {
    emoji: '😐',
    label: 'Neutro',
    description: 'neutro',
    guidance: 'Cliente aguardando uma resposta objetiva.',
    banner: 'bg-amber-50 border-amber-200 text-amber-900',
    pill: 'bg-amber-50 text-amber-800 border-amber-200',
  },
  negative: {
    emoji: '😠',
    label: 'Frustrado',
    description: 'negativo',
    guidance: 'Cliente frustrado — abordagem empática recomendada antes de qualquer oferta.',
    banner: 'bg-red-50 border-red-200 text-red-900',
    pill: 'bg-red-50 text-red-800 border-red-200',
  },
};

export function sentimentStyle(sentiment: Sentiment | null | undefined): SentimentStyle | null {
  return sentiment ? SENTIMENT_STYLES[sentiment] : null;
}
