/**
 * Urgência de uma conversa transferida pelo tempo que o cliente espera.
 *
 * Os limites são constantes de propósito: ajustá-los ao SLA da operação é
 * mudar um número aqui, e não procurar `if` espalhado pela tela.
 */
export const URGENCY_LIMITS_MINUTES = { medium: 5, high: 15, critical: 30 } as const;

export type UrgencyLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Urgency {
  level: UrgencyLevel;
  label: string;
  /** Classes do selo: fundo, texto e borda. */
  badge: string;
  /** Cor da barra lateral da linha. */
  bar: string;
}

const STYLES: Record<UrgencyLevel, Omit<Urgency, 'level'>> = {
  low: { label: 'No prazo', badge: 'bg-green-50 text-green-800 border-green-200',
         bar: 'bg-green-500' },
  medium: { label: 'Atenção', badge: 'bg-yellow-50 text-yellow-800 border-yellow-200',
            bar: 'bg-yellow-400' },
  high: { label: 'Urgente', badge: 'bg-orange-50 text-orange-800 border-orange-200',
          bar: 'bg-orange-500' },
  critical: { label: 'Crítico', badge: 'bg-red-50 text-red-800 border-red-200',
              bar: 'bg-red-600' },
};

export function urgencyLevel(seconds: number): UrgencyLevel {
  const minutes = seconds / 60;
  if (minutes >= URGENCY_LIMITS_MINUTES.critical) return 'critical';
  if (minutes >= URGENCY_LIMITS_MINUTES.high) return 'high';
  if (minutes >= URGENCY_LIMITS_MINUTES.medium) return 'medium';
  return 'low';
}

export function urgencyFor(seconds: number): Urgency {
  const level = urgencyLevel(seconds);
  return { level, ...STYLES[level] };
}

/** 83 min → "1h 23min"; 40 s → "< 1 min" */
export function formatWait(seconds: number): string {
  const minutes = Math.floor(Math.max(0, seconds) / 60);
  if (minutes < 1) return '< 1 min';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours < 24) return rest ? `${hours}h ${rest}min` : `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

/** Segundos de espera a partir do momento da transferência e de um "agora". */
export function secondsSince(isoMoment: string | null, now: number): number | null {
  if (!isoMoment) return null;
  const start = Date.parse(isoMoment);
  if (Number.isNaN(start)) return null;
  return Math.max(0, Math.floor((now - start) / 1000));
}
