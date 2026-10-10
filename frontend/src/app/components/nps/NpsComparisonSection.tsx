import { Scale } from 'lucide-react';

import { useNpsComparison } from '../../api/hooks';
import type { NpsComparison } from '../../api/types';
import { Loading } from '../AsyncBoundary';
import NpsComparisonCards from './NpsComparisonCards';
import NpsComparisonChart from './NpsComparisonChart';
import { score } from './format';

/**
 * Bloco do Dashboard: NPS do atendimento automatizado versus o humano.
 *
 * Carrega por conta própria para que uma falha aqui não derrube o resto do
 * painel — os KPIs continuam valendo mesmo que este cálculo não responda.
 */
export default function NpsComparisonSection({ area, pollMs = 8000 }: {
  area: string; pollMs?: number;
}) {
  const state = useNpsComparison(area, pollMs);

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-5"
             aria-labelledby="nps-comparison-title">
      <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
        <div>
          <h3 id="nps-comparison-title" className="font-semibold text-gray-900 flex items-center gap-2">
            <Scale className="w-4 h-4 text-[#E10019]" aria-hidden />
            Comparativo de NPS: Bot vs Atendente
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Conta como humano todo atendimento com transferência, resposta ou encerramento
            feito por um atendente.
          </p>
        </div>
        {state.data && <Headline data={state.data} />}
      </div>

      {state.loading && !state.data && <Loading label="Calculando o comparativo…" />}
      {state.error && !state.data && (
        <p className="text-sm text-gray-500 py-6 text-center">
          Não foi possível calcular o comparativo agora.
        </p>
      )}
      {state.data && (
        state.data.overall.total === 0 ? (
          <p className="text-sm text-gray-500 py-8 text-center">
            Nenhuma nota de satisfação registrada nesta área ainda. Encerre um atendimento
            pelo bot e outro pelo console para ver a comparação.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
              <NpsComparisonCards data={state.data} />
              <NpsComparisonChart data={state.data} />
            </div>
            <p className="mt-3 text-[11px] text-gray-400">
              Promotores: notas 9–10 · Neutros: 7–8 · Detratores: 0–6 · NPS = % promotores − %
              detratores. Só notas respondidas entram no cálculo.
            </p>
          </>
        )
      )}
    </section>
  );
}

/** A frase que responde à pergunta do bloco, sem o leitor precisar fazer conta. */
function Headline({ data }: { data: NpsComparison }) {
  const diff = data.comparison.score_difference;
  if (diff == null) return null;

  const text = diff === 0
    ? 'Bot e atendente empatados na nota média'
    : `Atendente ${diff > 0 ? 'à frente' : 'atrás'} do bot por ${score(Math.abs(diff))} ponto${Math.abs(diff) === 1 ? '' : 's'} na nota média`;
  const tone = diff > 0 ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
    : diff < 0 ? 'bg-indigo-50 text-indigo-800 border-indigo-200'
    : 'bg-gray-50 text-gray-700 border-gray-200';

  return (
    <p className={`text-xs font-medium px-3 py-1.5 rounded-full border ${tone}`} role="status">
      {text}
    </p>
  );
}
