import { cn } from '../ui/utils';

/** Limites de cor da franquia: verde até 60%, amarelo até 80%, vermelho acima. */
export const CONSUMPTION_LIMITS = { warning: 60, critical: 80 } as const;

export function consumptionTone(percent: number): 'ok' | 'warning' | 'critical' {
  if (percent >= CONSUMPTION_LIMITS.critical) return 'critical';
  if (percent >= CONSUMPTION_LIMITS.warning) return 'warning';
  return 'ok';
}

const TONES = {
  ok: { bar: 'bg-green-500', text: 'text-green-700', label: 'dentro da franquia' },
  warning: { bar: 'bg-yellow-400', text: 'text-yellow-700', label: 'atenção ao consumo' },
  critical: { bar: 'bg-red-500', text: 'text-red-700', label: 'perto do limite' },
} as const;

const number = (value: number) =>
  Number.isInteger(value) ? String(value) : value.toFixed(1).replace('.', ',');

/** Barra de consumo da franquia, com valor e situação também em texto. */
export default function ConsumptionBar({ current, total, unit = 'GB', label }: {
  current: number; total: number; unit?: string; label?: string;
}) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  const tone = TONES[consumptionTone(percent)];
  const text = label ?? `${number(current)}${unit} de ${number(total)}${unit}`;

  return (
    <div>
      <div className="flex items-baseline justify-between text-xs mb-1">
        <span className="text-gray-600">{text}</span>
        <span className={cn('font-semibold', tone.text)}>{percent}%</span>
      </div>
      <div
        role="progressbar"
        aria-label={`Consumo da franquia: ${text}, ${tone.label}`}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        className="w-full h-2 rounded-full bg-gray-100 overflow-hidden"
      >
        <div className={cn('h-2 rounded-full transition-all', tone.bar)}
             style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
      <p className={cn('text-[11px] mt-1', tone.text)}>{tone.label}</p>
    </div>
  );
}
