import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import Dashboard from './Dashboard';

vi.mock('../../api/client', () => ({
  api: { getDashboard: vi.fn(), getNpsComparison: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.getNpsComparison.mockResolvedValue(fixtures.npsComparison);
});

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

describe('comparativo de NPS bot vs atendente', () => {
  it('mostra os dois grupos com nota média e distribuição', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.filledDashboard);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText('Comparativo de NPS: Bot vs Atendente')).toBeInTheDocument();
    const bot = await screen.findByRole('article', { name: /Atendido pelo bot/ });
    const humano = screen.getByRole('article', { name: /Atendido por humano/ });
    expect(bot).toHaveTextContent('6,8');
    expect(bot).toHaveTextContent('2 pesquisa(s) sem resposta');
    expect(humano).toHaveTextContent('8,6');
    expect(humano).toHaveTextContent('+60');
  });

  it('resume a diferença numa frase', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.filledDashboard);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText(/Atendente à frente do bot por 1,8 pontos/))
      .toBeInTheDocument();
  });

  it('explica quando ainda não há notas', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.filledDashboard);
    mocked.getNpsComparison.mockResolvedValue(fixtures.emptyNpsComparison);

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText(/Nenhuma nota de satisfação registrada/)).toBeInTheDocument();
  });

  it('não derruba o painel quando o comparativo falha', async () => {
    mocked.getDashboard.mockResolvedValue(fixtures.filledDashboard);
    mocked.getNpsComparison.mockRejectedValue(new Error('falhou'));

    renderAt(<Dashboard />, { route: '/console' });

    expect(await screen.findByText('Taxa de Resolução')).toBeInTheDocument();
    expect(await screen.findByText(/Não foi possível calcular o comparativo/))
      .toBeInTheDocument();
  });
});
