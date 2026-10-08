import { describe, expect, it } from 'vitest';

import * as fixtures from '../../../test/fixtures';
import { toRows } from './NpsComparisonChart';
import { pct, score, signed } from './format';

describe('formatação do comparativo de NPS', () => {
  it('usa vírgula decimal e travessão para ausência', () => {
    expect(score(8.25)).toBe('8,3');
    expect(score(null)).toBe('—');
  });

  it('mostra percentual inteiro sem casa decimal', () => {
    expect(pct(40)).toBe('40%');
    expect(pct(33.3)).toBe('33,3%');
  });

  it('dá sinal ao NPS', () => {
    expect(signed(60)).toBe('+60');
    expect(signed(-10)).toBe('−10');
    expect(signed(0)).toBe('0');
  });

  it('monta uma linha por categoria com percentual e contagem dos dois grupos', () => {
    const rows = toRows(fixtures.npsComparison);

    expect(rows.map((r) => r.category)).toEqual(['Promotores', 'Neutros', 'Detratores']);
    expect(rows[0]).toEqual({ category: 'Promotores', bot: 30, agent: 60, botCount: 3,
                              agentCount: 3 });
  });
});
