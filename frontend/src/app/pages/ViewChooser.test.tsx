import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api, ApiError } from '../api/client';
import * as fixtures from '../../test/fixtures';
import { renderAt } from '../../test/render';
import ViewChooser from './ViewChooser';

vi.mock('../api/client', () => ({
  api: { getHealth: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.getHealth.mockResolvedValue(fixtures.health);
});

describe('escolha de visão', () => {
  it('separa o lado do cliente do lado da Claro', async () => {
    renderAt(<ViewChooser />);

    expect(await screen.findByRole('link', { name: /Sou o cliente/ }))
      .toHaveAttribute('href', '/simulador');
    expect(screen.getByRole('link', { name: /Sou a Claro/ }))
      .toHaveAttribute('href', '/console');
  });

  it('avisa quando o assistente está sem IA generativa', async () => {
    renderAt(<ViewChooser />);

    expect(await screen.findByText(/respostas por modelo de texto/)).toBeInTheDocument();
    expect(screen.getByText(/LLM_API_KEY/)).toBeInTheDocument();
  });

  it('confirma quando a redação generativa está ativa', async () => {
    mocked.getHealth.mockResolvedValue({
      ...fixtures.health,
      components: { ...fixtures.health.components, generative_ai: true },
    });

    renderAt(<ViewChooser />);

    expect(await screen.findByText(/respostas escritas por IA generativa/)).toBeInTheDocument();
    expect(screen.queryByText(/LLM_API_KEY/)).not.toBeInTheDocument();
  });

  it('mostra que a API está fora do ar sem esconder as duas visões', async () => {
    mocked.getHealth.mockRejectedValue(new ApiError(0, 'Não foi possível alcançar a API do hub.'));

    renderAt(<ViewChooser />);

    expect(await screen.findByText('API indisponível')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Sou o cliente/ })).toBeInTheDocument();
  });
});
