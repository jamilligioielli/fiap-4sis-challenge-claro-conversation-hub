import { cn } from '../ui/utils';

export type NpsCategory = 'promotor' | 'neutro' | 'detrator';

/** Mesmas faixas do back-end: 0–6 detrator, 7–8 neutro, 9–10 promotor. */
export function categoryFor(score: number): NpsCategory {
  if (score <= 6) return 'detrator';
  if (score <= 8) return 'neutro';
  return 'promotor';
}

const STYLES: Record<NpsCategory, { label: string; className: string; dot: string }> = {
  promotor: { label: 'Promotor', className: 'bg-green-50 text-green-800 border-green-200',
              dot: 'bg-green-500' },
  neutro: { label: 'Neutro', className: 'bg-yellow-50 text-yellow-800 border-yellow-200',
            dot: 'bg-yellow-400' },
  detrator: { label: 'Detrator', className: 'bg-red-50 text-red-800 border-red-200',
              dot: 'bg-red-500' },
};

/** Nota de NPS com a categoria por extenso: "7 (Neutro)". */
export default function NpsHistoryBadge({ score, category }: {
  score: number | null | undefined; category?: string | null;
}) {
  if (score == null) {
    return <span className="text-xs text-gray-500">Sem nota registrada</span>;
  }
  const key: NpsCategory = category === 'promotor' || category === 'neutro'
    || category === 'detrator' ? category : categoryFor(score);
  const style = STYLES[key];
  const value = Number.isInteger(score) ? String(score) : score.toFixed(1).replace('.', ',');

  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold border',
                        style.className)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', style.dot)} aria-hidden />
      {value} ({style.label})
    </span>
  );
}
