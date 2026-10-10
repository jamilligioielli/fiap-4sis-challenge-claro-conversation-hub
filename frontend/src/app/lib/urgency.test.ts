import { describe, expect, it } from 'vitest';

import { formatWait, secondsSince, urgencyFor, urgencyLevel } from './urgency';

describe('urgência pela espera', () => {
  it.each([
    [0, 'low'], [4 * 60 + 59, 'low'], [5 * 60, 'medium'], [14 * 60, 'medium'],
    [15 * 60, 'high'], [29 * 60, 'high'], [30 * 60, 'critical'], [3 * 3600, 'critical'],
  ])('%i segundos → %s', (seconds, level) => {
    expect(urgencyLevel(seconds)).toBe(level);
  });

  it('dá rótulo em texto além da cor', () => {
    expect(urgencyFor(31 * 60).label).toBe('Crítico');
    expect(urgencyFor(60).label).toBe('No prazo');
  });
});

describe('formatação do tempo de espera', () => {
  it.each([
    [30, '< 1 min'], [60, '1 min'], [23 * 60, '23 min'], [60 * 60, '1h'],
    [83 * 60, '1h 23min'], [26 * 3600, '1d 2h'],
  ])('%i segundos → %s', (seconds, text) => {
    expect(formatWait(seconds)).toBe(text);
  });

  it('calcula a espera desde a transferência', () => {
    const now = Date.parse('2026-10-05T12:10:00Z');
    expect(secondsSince('2026-10-05T12:00:00Z', now)).toBe(600);
    expect(secondsSince(null, now)).toBeNull();
    expect(secondsSince('lixo', now)).toBeNull();
  });
});
