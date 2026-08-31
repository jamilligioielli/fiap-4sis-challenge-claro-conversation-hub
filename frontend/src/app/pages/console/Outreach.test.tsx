import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import Outreach from './Outreach';

vi.mock('../../api/client', () => ({
  api: { listEligibleCustomers: vi.fn(), sendOutreach: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.listEligibleCustomers.mockResolvedValue([
    fixtures.eligibleContactable, fixtures.eligibleBlocked,
  ]);
  mocked.sendOutreach.mockResolvedValue({
    conversation_id: 'conv9', customer_id: 'cus1', message: 'Oi, Maria!',
    channel: 'whatsapp', template_category: 'marketing', used_template: false,
    response_source: 'generative',
  });
});

describe('elegibilidade', () => {
  it('mostra por que cada cliente foi indicado', async () => {
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    expect(await screen.findByText('Usa 92% da franquia todo mês')).toBeInTheDocument();
    expect(screen.getByText('Cliente há mais de 5 anos')).toBeInTheDocument();
  });

  it('mostra os impedimentos com o mesmo destaque dos motivos', async () => {
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    expect(await screen.findByText(/Contato bloqueado/)).toBeInTheDocument();
    expect(screen.getByText(/não autorizou receber ofertas/)).toBeInTheDocument();
  });

  it('informa o estado do consentimento de cada cliente', async () => {
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    expect(await screen.findByText('aceita receber ofertas')).toBeInTheDocument();
    expect(screen.getByText('sem consentimento para oferta')).toBeInTheDocument();
  });

  it('informa o estado da janela de 24 horas', async () => {
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    expect(await screen.findByText(/janela de 24h aberta · 18h restantes/)).toBeInTheDocument();
    expect(screen.getByText('janela de 24h fechada')).toBeInTheDocument();
  });

  it('avisa quando o envio exigiria modelo aprovado', async () => {
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    expect(await screen.findByText('exige modelo aprovado')).toBeInTheDocument();
  });
});

describe('envio da abordagem', () => {
  it('bloqueia o botão de quem não pode ser contatado', async () => {
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    const botoes = await screen.findAllByRole('button', { name: /Abordar cliente/ });
    expect(botoes[0]).toBeEnabled();
    expect(botoes[1]).toBeDisabled();
  });

  it('envia a oferta sugerida para o cliente elegível', async () => {
    const user = userEvent.setup();
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    const botoes = await screen.findAllByRole('button', { name: /Abordar cliente/ });
    await user.click(botoes[0]);

    await waitFor(() => expect(mocked.sendOutreach)
      .toHaveBeenCalledWith('cus1', 'offer-flex-50'));
  });

  it('mostra o resultado e o caminho para a conversa criada', async () => {
    const user = userEvent.setup();
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    const botoes = await screen.findAllByRole('button', { name: /Abordar cliente/ });
    await user.click(botoes[0]);

    expect(await screen.findByText('abordagem enviada')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /ver a conversa/ }))
      .toHaveAttribute('href', '/console/conversation/conv9');
  });

  it('mostra o erro quando a API recusa o envio', async () => {
    const user = userEvent.setup();
    mocked.sendOutreach.mockRejectedValue(new Error('Cliente sem consentimento'));
    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    const botoes = await screen.findAllByRole('button', { name: /Abordar cliente/ });
    await user.click(botoes[0]);

    expect(await screen.findByText('Cliente sem consentimento')).toBeInTheDocument();
  });
});

describe('lista vazia', () => {
  it('não inventa candidatos quando não há ninguém elegível', async () => {
    mocked.listEligibleCustomers.mockResolvedValue([]);

    renderAt(<Outreach />, { route: '/console/contato-ativo' });

    expect(await screen.findByText('Ninguém elegível no momento')).toBeInTheDocument();
  });
});
