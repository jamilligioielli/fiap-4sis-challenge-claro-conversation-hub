import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import Dashboard from './Dashboard';

vi.mock('../../api/client', () => ({
  api: { getDashboard: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

beforeEach(() => vi.clearAllMocks());

describe('painel sem dados', () => {
  it('não mostra indicador nenhum antes da primeira conversa', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.emptyDashboard);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText('Nenhuma conversa processada ainda')).toBeInTheDocument();
    expect(screen.queryByText('Taxa de Resolução')).not.toBeInTheDocument();
  });

  it('deixa claro que o vazio é decisão, não falha', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.emptyDashboard);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText(/começa vazio de propósito/)).toBeInTheDocument();
  });

  it('leva ao simulador, que é o que preenche o painel', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.emptyDashboard);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByRole('link', { name: /Abrir o simulador/ }))
      .toHaveAttribute('href', '/simulador');
  });
});

describe('painel alimentado pelas conversas', () => {
  it('mostra os indicadores calculados quando há dados', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.filledDashboard);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText('Taxa de Resolução')).toBeInTheDocument();
    expect(screen.getByText('64')).toBeInTheDocument();
    expect(screen.getByText('75,0%')).toBeInTheDocument();
  });

  it('formata percentuais e milhares no padrão brasileiro', async () => {
    mocked.getDashboard.mockResolvedValue({
      ...fixtures.filledDashboard,
      conversations: { value: 1500, trend: 4, unit: '' },
    });

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText('1,5k')).toBeInTheDocument();
    expect(screen.getByText('8,3%')).toBeInTheDocument();
  });

  it('filtra por área ao clicar no seletor', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.filledDashboard);

    renderAt(<Dashboard />, { route: '/console' });
    await screen.findByText('Taxa de Resolução');

    expect(mocked.getDashboard).toHaveBeenCalledWith(undefined);
  });
});
