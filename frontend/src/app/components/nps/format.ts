/**
 * Formatação e cores do comparativo de NPS.
 *
 * As cores das séries passaram pelo validador de paleta (daltonismo e
 * contraste): o cinza originalmente previsto para o bot ficava indistinguível
 * do verde para quem tem deuteranopia. Índigo e esmeralda passam em todas as
 * verificações; o verde segue o mesmo tom dos balões do atendente na conversa.
 */
export const SERIES = {
  bot: { label: 'Bot', color: '#6366F1' },
  agent: { label: 'Atendente', color: '#059669' },
} as const;

export type SeriesKey = keyof typeof SERIES;

export const CATEGORIES = [
  { key: 'promoters', label: 'Promotores', range: '9–10', dot: 'bg-green-500' },
  { key: 'passives', label: 'Neutros', range: '7–8', dot: 'bg-amber-400' },
  { key: 'detractors', label: 'Detratores', range: '0–6', dot: 'bg-red-500' },
] as const;

/** 8.25 → "8,3" */
export function score(value: number | null): string {
  return value == null ? '—' : value.toFixed(1).replace('.', ',');
}

/** 45.5 → "45,5%" (inteiro quando exato) */
export function pct(value: number): string {
  const text = Number.isInteger(value) ? String(value) : value.toFixed(1).replace('.', ',');
  return `${text}%`;
}

/** NPS com sinal: +40, −12, 0 */
export function signed(value: number | null): string {
  if (value == null) return '—';
  const rounded = Math.round(value);
  if (rounded > 0) return `+${rounded}`;
  if (rounded < 0) return `−${Math.abs(rounded)}`;
  return '0';
}
