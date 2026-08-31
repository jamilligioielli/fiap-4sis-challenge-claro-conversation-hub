import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api, ApiError } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import SimulatorChat from './SimulatorChat';

vi.mock('../../api/client', () => ({
  api: {
    startConversation: vi.fn(),
    sendAsCustomer: vi.fn(),
    getConversation: vi.fn(),
    getCustomerContext: vi.fn(),
    listCustomerConversations: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

function renderChat() {
  return renderAt(<SimulatorChat />, {
    path: '/simulador/:customerId',
    route: '/simulador/cus1',
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mocked.getCustomerContext.mockResolvedValue(fixtures.customerContext);
  mocked.listCustomerConversations.mockResolvedValue([]);
  mocked.startConversation.mockResolvedValue(fixtures.greeting);
  mocked.sendAsCustomer.mockResolvedValue(fixtures.hubReply);
  mocked.getConversation.mockResolvedValue(fixtures.conversationDetail);
});

describe('abertura da conversa', () => {
  it('abre a conversa pelo cliente da URL, sem pedir identificação', async () => {
    renderChat();

    await waitFor(() => expect(mocked.startConversation).toHaveBeenCalledWith('cus1', 'whatsapp'));
    expect(await screen.findByText(/Sou a Clara/)).toBeInTheDocument();
    expect(screen.queryByText(/não identificado/i)).not.toBeInTheDocument();
  });

  it('mostra o nome e o plano do cliente escolhido no cabeçalho', async () => {
    renderChat();

    expect(await screen.findByText('Maria Silva Santos')).toBeInTheDocument();
    expect(screen.getByText(/Claro Flex 30GB/)).toBeInTheDocument();
  });

  it('retoma a conversa em andamento em vez de gerar outra saudação', async () => {
    mocked.startConversation.mockResolvedValue({ ...fixtures.greeting, greeting: '', resumed: true });

    renderChat();

    await waitFor(() => expect(mocked.getConversation).toHaveBeenCalledWith('conv1'));
    expect(await screen.findByText('Quero mais internet')).toBeInTheDocument();
  });
});

describe('troca de canal', () => {
  it('registra a troca na transcrição sem reabrir a conversa', async () => {
    const user = userEvent.setup();
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.click(screen.getByRole('button', { name: /App Claro/ }));

    expect(await screen.findByText(/Você abriu o App Claro/)).toBeInTheDocument();
    expect(mocked.startConversation).toHaveBeenCalledTimes(1);
  });

  it('oferece continuar ou trocar de assunto quando o hub pergunta', async () => {
    const user = userEvent.setup();
    mocked.sendAsCustomer.mockResolvedValue(fixtures.awaitingReply);
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.type(screen.getByRole('textbox'), 'oi de novo{Enter}');

    expect(await screen.findByRole('button', { name: /Continuar nesse assunto/ }))
      .toBeInTheDocument();
    expect(screen.getByRole('button', { name: /É outro assunto/ })).toBeInTheDocument();
  });

  it('responde a pergunta de continuidade pelo canal atual', async () => {
    const user = userEvent.setup();
    mocked.sendAsCustomer.mockResolvedValue(fixtures.awaitingReply);
    renderChat();
    await screen.findByText(/Sou a Clara/);
    await user.type(screen.getByRole('textbox'), 'oi{Enter}');

    await user.click(await screen.findByRole('button', { name: /Continuar nesse assunto/ }));

    expect(mocked.sendAsCustomer).toHaveBeenLastCalledWith('whatsapp', {
      text: 'Sim, quero continuar nesse assunto', customer_id: 'cus1',
    });
  });
});

describe('canal de voz', () => {
  it('não oferece simulação por escrito — só a informação de que é por ligação', async () => {
    const user = userEvent.setup();
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.click(screen.getByRole('button', { name: /Ligar para a Claro/ }));

    expect(await screen.findByText(/atende por ligação/)).toBeInTheDocument();
    expect(screen.getByText(/próxima versão/)).toBeInTheDocument();
  });
});

describe('envio de mensagem', () => {
  it('manda a mensagem amarrada ao cliente escolhido', async () => {
    const user = userEvent.setup();
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.type(screen.getByRole('textbox'), 'Quero mais internet{Enter}');

    await waitFor(() => expect(mocked.sendAsCustomer).toHaveBeenCalledWith('whatsapp', {
      text: 'Quero mais internet', customer_id: 'cus1',
    }));
    expect(await screen.findByText(/Posso te mostrar o Flex 50GB/)).toBeInTheDocument();
  });

  it('mostra que a resposta foi escrita por IA generativa', async () => {
    const user = userEvent.setup();
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.type(screen.getByRole('textbox'), 'oi{Enter}');

    await screen.findByText(/Posso te mostrar o Flex 50GB/);
    expect(screen.getAllByText(/escrito por IA/).length).toBeGreaterThan(0);
    expect(screen.getByText('llama-3.3-70b-versatile')).toBeInTheDocument();
  });

  it('devolve o texto ao campo quando o envio falha', async () => {
    const user = userEvent.setup();
    mocked.sendAsCustomer.mockRejectedValue(new Error('API fora do ar'));
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.type(screen.getByRole('textbox'), 'oi{Enter}');

    expect(await screen.findByText('API fora do ar')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveValue('oi');
  });

  it('expõe a versão da persona que produziu a resposta', async () => {
    const user = userEvent.setup();
    renderChat();
    await screen.findByText(/Sou a Clara/);

    await user.type(screen.getByRole('textbox'), 'oi{Enter}');

    expect(await screen.findByText('v3')).toBeInTheDocument();
  });
});

describe('histórico do cliente', () => {
  it('avisa que ainda não há conversas guardadas', async () => {
    renderChat();

    expect(await screen.findByText(/Nenhuma ainda/)).toBeInTheDocument();
  });

  it('lista as conversas anteriores e permite reabrir uma', async () => {
    const user = userEvent.setup();
    mocked.listCustomerConversations.mockResolvedValue([fixtures.conversationItem]);
    renderChat();

    const historico = await screen.findByRole('button', { name: /Alteração de Plano/ });
    await user.click(historico);

    await waitFor(() => expect(mocked.getConversation).toHaveBeenCalledWith('conv1'));
    expect(await screen.findByText('Quero mais internet')).toBeInTheDocument();
  });

  it('marca com destaque as conversas que a Claro iniciou', async () => {
    mocked.listCustomerConversations.mockResolvedValue([
      { ...fixtures.conversationItem, initiated_by_company: true },
    ]);
    renderChat();

    expect(await screen.findByText(/a Claro iniciou/)).toBeInTheDocument();
  });
});

describe('integração com o console', () => {
  it('não expõe configuração de integração de canal para quem simula o cliente', async () => {
    renderChat();
    await screen.findByText(/Sou a Clara/);

    expect(screen.queryByText(/access token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/phone number id/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/webhook/i)).not.toBeInTheDocument();
  });

  it('liga a conversa atual à visão da Claro', async () => {
    renderChat();

    const link = await screen.findByRole('link', { name: /Abrir esta conversa no console/ });
    expect(link).toHaveAttribute('href', '/console/conversation/conv1');
  });

  it('permite voltar à escolha de cliente', async () => {
    renderChat();

    const voltar = await screen.findByRole('link', { name: /Trocar de cliente/ });
    expect(voltar).toHaveAttribute('href', '/simulador');
  });
});

describe('falhas de carregamento', () => {
  it('explica quando a API não responde', async () => {
    mocked.getCustomerContext.mockRejectedValue(
      new ApiError(0, 'Não foi possível alcançar a API do hub.'));

    renderChat();

    expect(await screen.findByText(/API do hub indisponível/)).toBeInTheDocument();
  });

  it('mostra o erro quando a conversa não abre', async () => {
    mocked.startConversation.mockRejectedValue(new Error('Cliente não encontrado'));

    renderChat();

    const composer = await screen.findByRole('textbox');
    expect(within(composer.closest('div')!.parentElement!).getByText('Cliente não encontrado'))
      .toBeInTheDocument();
  });
});
