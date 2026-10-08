import { CheckCircle2 } from 'lucide-react';

import { cn } from '../ui/utils';

/** Aceita 0–1 ou 0–100 e devolve sempre 0–1. */
export function normalizeConfidence(score: number): number {
  return score > 1 ? Math.min(score / 100, 1) : Math.max(score, 0);
}

export function confidenceTone(score: number): 'high' | 'medium' | 'low' {
  const value = normalizeConfidence(score);
  if (value > 0.9) return 'high';
  if (value >= 0.7) return 'medium';
  return 'low';
}

const TONES = {
  high: { className: 'bg-green-50 text-green-800 border-green-200', text: 'confiança alta' },
  medium: { className: 'bg-yellow-50 text-yellow-800 border-yellow-200', text: 'confiança média' },
  low: { className: 'bg-red-50 text-red-800 border-red-200', text: 'confiança baixa' },
} as const;

/** Selo da confiança da intenção — percentual, cor e, acima de 90%, o ✓. */
export default function ConfidenceBadge({ score, label }: {
  score: number | null | undefined; label?: string;
}) {
  if (score == null) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs border bg-gray-50 text-gray-500 border-gray-200">
        sem classificação
      </span>
    );
  }
  const value = normalizeConfidence(score);
  const tone = confidenceTone(value);
  const text = label ?? `${Math.round(value * 100)}%`;

  return (
    <span
      className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border',
                    TONES[tone].className)}
      title={`Classificação com ${TONES[tone].text}`}
      aria-label={`${text} de confiança (${TONES[tone].text})`}
    >
      {text}
      {tone === 'high' && <CheckCircle2 className="w-3.5 h-3.5" aria-hidden />}
    </span>
  );
}
