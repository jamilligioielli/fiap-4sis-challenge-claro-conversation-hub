import { CircleCheck, CircleX, Hourglass, HeartCrack, Info, ShoppingCart, Receipt, Wrench } from 'lucide-react';

import type { HistoryStatus, HistoryType } from '../../api/types';

/** Ícone e rótulo por tipo de atendimento. */
export const TYPE_STYLES: Record<HistoryType, { icon: typeof Info; className: string }> = {
  vendas: { icon: ShoppingCart, className: 'bg-green-50 text-green-700' },
  suporte: { icon: Wrench, className: 'bg-blue-50 text-blue-700' },
  financeiro: { icon: Receipt, className: 'bg-amber-50 text-amber-700' },
  cancelamento: { icon: HeartCrack, className: 'bg-red-50 text-red-700' },
  consulta: { icon: Info, className: 'bg-violet-50 text-violet-700' },
};

/** Situação: cor da bolinha, ícone e selo. */
export const STATUS_STYLES: Record<HistoryStatus, {
  icon: typeof Info; dot: string; badge: string;
}> = {
  open: { icon: Hourglass, dot: 'bg-amber-400 ring-amber-100',
          badge: 'bg-amber-50 text-amber-800 border-amber-200' },
  resolved: { icon: CircleCheck, dot: 'bg-green-500 ring-green-100',
              badge: 'bg-green-50 text-green-800 border-green-200' },
  unresolved: { icon: CircleX, dot: 'bg-red-500 ring-red-100',
                badge: 'bg-red-50 text-red-800 border-red-200' },
};

/** "2026-10-05" → "05/10/2026"; com `short`, "05/10". */
export function formatDate(isoDate: string, short = false): string {
  const [year, month, day] = isoDate.slice(0, 10).split('-');
  if (!year || !month || !day) return isoDate;
  return short ? `${day}/${month}` : `${day}/${month}/${year}`;
}
