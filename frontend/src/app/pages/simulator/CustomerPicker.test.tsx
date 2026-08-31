import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api, ApiError } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import CustomerPicker from './CustomerPicker';

vi.mock('../../api/client', () => ({
  api: { listCustomers: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.listCustomers.mockResolvedValue([
    fixtures.customerSummary, fixtures.customerWithoutOptIn,
  ]);
});

describe('escolha da persona', () => {
  it('lista os clientes disponíveis para simular', async () => {
    renderAt(<CustomerPicker />, { route: '/simulador' });

    expect(await screen.findByText('Maria Silva Santos')).toBeInTheDocument();
    expect(screen.getByText('Felipe Barros')).toBeInTheDocument();
  });

  it('leva para o simulador daquele cliente', async () => {
    renderAt(<CustomerPicker />, { route: '/simulador' });

    const card = await screen.findByRole('link', { name: /Maria Silva Santos/ });
    expect(card).toHaveAttribute('href', '/simulador/cus1');
  });

  it('mostra o contexto que o assistente vai usar', async () => {
    renderAt(<CustomerPicker />, { route: '/simulador' });

    expect(await screen.findByText(/Usa quase toda a franquia/)).toBeInTheDocument();
    expect(screen.getByText('Claro Flex 30GB')).toBeInTheDocument();
    expect(screen.getByText('92% da franquia')).toBeInTheDocument();
  });

  it('distingue quem aceita oferta de quem não deu consentimento', async () => {
    renderAt(<CustomerPicker />, { route: '/simulador' });

    expect(await screen.findByText('aceita ofertas')).toBeInTheDocument();
    expect(screen.getByText('sem opt-in')).toBeInTheDocument();
  });

  it('sinaliza risco de saída e segmento VIP', async () => {
    renderAt(<CustomerPicker />, { route: '/simulador' });

    expect(await screen.findByText('VIP')).toBeInTheDocument();
    expect(screen.getByText('risco de saída')).toBeInTheDocument();
  });

  it('mostra quantas conversas cada cliente já teve', async () => {
    renderAt(<CustomerPicker />, { route: '/simulador' });

    expect(await screen.findByText('2 conversas')).toBeInTheDocument();
  });

  it('explica quando a API não responde', async () => {
    mocked.listCustomers.mockRejectedValue(
      new ApiError(0, 'Não foi possível alcançar a API do hub.'));

    renderAt(<CustomerPicker />, { route: '/simulador' });

    expect(await screen.findByText(/API do hub indisponível/)).toBeInTheDocument();
  });
});
