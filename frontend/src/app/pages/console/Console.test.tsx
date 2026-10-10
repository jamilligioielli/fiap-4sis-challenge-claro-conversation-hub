import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api, ApiError } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import ConsoleLayout from './ConsoleLayout';
import Conversation from './Conversation';
import CustomerContext from './CustomerContext';
import Inbox from './Inbox';
import PersonaImpact from './PersonaImpact';

vi.mock('../../api/client', () => ({
  api: {
    getHealth: vi.fn(),
    listConversations: vi.fn(),
    getConversation: vi.fn(),
    getCustomerContext: vi.fn(),
    getConversationHistory: vi.fn(),
    replyAsAgent: vi.fn(),
    requestHandover: vi.fn(),
    closeConversation: vi.fn(),
    previewPersona: vi.fn(),
    listCustomers: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.getHealth.mockResolvedValue(fixtures.health);
  mocked.listConversations.mockResolvedValue([fixtures.conversationItem]);
  mocked.getConversation.mockResolvedValue(fixtures.conversationDetail);
  mocked.getCustomerContext.mockResolvedValue(fixtures.customerContext);
  mocked.listCustomers.mockResolvedValue([fixtures.customerSummary]);
  mocked.getConversationHistory.mockResolvedValue(fixtures.conversationHistory);
});

// ================================================================== moldura
describe('moldura do console', () => {
  it('no celular a navegação vira uma faixa sob o cabeçalho', async () => {
    renderAt(<ConsoleLayout />, { route: '/console/inbox-atendente' });

    const faixa = await screen.findByRole('navigation', { name: 'Navegação do console' });
    expect(faixa.className).toContain('md:hidden');
    expect(within(faixa).getByRole('link', { name: /Inbox do Atendente/ }).className)
      .toContain('text-[#E10019]');
  });

  it('não oferece o simulador dentro do console', async () => {
    renderAt(<ConsoleLayout />, { route: '/console' });

    const menu = await screen.findByRole('navigation', { name: 'Menu principal' });
    expect(within(menu).getByRole('link', { name: /Dashboard/ })).toBeInTheDocument();
    expect(within(menu).getByRole('link', { name: /Inbox Omnichannel/ })).toBeInTheDocument();
    expect(within(menu).getByRole('link', { name: /Inbox do Atendente/ }))
      .toHaveAttribute('href', '/console/inbox-atendente');
    expect(within(menu).getByRole('link', { name: /Contato Ativo/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Simulador/ })).not.toBeInTheDocument();
  });

  it('permite voltar à escolha de visão', () => {
    renderAt(<ConsoleLayout />, { route: '/console' });

    expect(screen.getByRole('link', { name: /Trocar de visão/ }))
      .toHaveAttribute('href', '/');
  });

  it('mostra em que modo o hub está rodando', async () => {
    renderAt(<ConsoleLayout />, { route: '/console' });

    expect(await screen.findByText(/respostas por modelo de texto/)).toBeInTheDocument();
    expect(screen.getByText(/API operacional/)).toBeInTheDocument();
  });

  it('avisa quando a API não responde', async () => {
    mocked.getHealth.mockRejectedValue(new ApiError(0, 'fora do ar'));

    renderAt(<ConsoleLayout />, { route: '/console' });

    expect(await screen.findByText('API indisponível')).toBeInTheDocument();
  });
});

// ==================================================================== inbox
describe('inbox', () => {
  it('lista as conversas que passaram pelo hub', async () => {
    renderAt(<Inbox />, { route: '/console/inbox' });

    expect(await screen.findAllByText('Maria Silva Santos')).not.toHaveLength(0);
    expect(screen.getAllByText(/Posso te mostrar o Flex 50GB/).length).toBeGreaterThan(0);
  });

  it('explica que a fila vazia é consequência, não falha', async () => {
    mocked.listConversations.mockResolvedValue([]);

    renderAt(<Inbox />, { route: '/console/inbox' });

    expect(await screen.findByText('A fila está vazia')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Abrir o simulador/ }))
      .toHaveAttribute('href', '/simulador');
  });

  it('abre o detalhe ao selecionar uma conversa', async () => {
    const user = userEvent.setup();
    renderAt(<Inbox />, { route: '/console/inbox' });

    const linhas = await screen.findAllByText('Maria Silva Santos');
    await user.click(linhas[0]);

    expect(await screen.findByRole('link', { name: /conversa/i })).toBeInTheDocument();
  });

  it('filtra a fila pela busca', async () => {
    const user = userEvent.setup();
    renderAt(<Inbox />, { route: '/console/inbox' });
    await screen.findAllByText('Maria Silva Santos');

    await user.type(screen.getByPlaceholderText(/buscar/i), 'Maria');

    await waitFor(() => expect(mocked.listConversations).toHaveBeenCalledWith(
      expect.objectContaining({ search: 'Maria' })));
  });

  it('mostra o erro quando a API falha', async () => {
    mocked.listConversations.mockRejectedValue(
      new ApiError(0, 'Não foi possível alcançar a API do hub.'));

    renderAt(<Inbox />, { route: '/console/inbox' });

    expect(await screen.findByText(/API do hub indisponível/)).toBeInTheDocument();
  });
});

// ================================================================= conversa
describe('conversa ativa', () => {
  function renderConversation() {
    return renderAt(<Conversation />, {
      path: '/console/conversation/:id', route: '/console/conversation/conv1',
    });
  }

  it('mostra a transcrição completa', async () => {
    renderConversation();

    expect(await screen.findByText('Quero mais internet')).toBeInTheDocument();
    expect(screen.getByText('Oi, Maria! 👋')).toBeInTheDocument();
  });

  it('entrega o contexto pronto ao atendente', async () => {
    renderConversation();

    expect(await screen.findAllByText(/Alteração de Plano/)).not.toHaveLength(0);
  });

  it('envia a resposta do atendente e recarrega a transcrição', async () => {
    const user = userEvent.setup();
    mocked.replyAsAgent.mockResolvedValue(fixtures.conversationDetail.messages[0]);
    renderConversation();
    await screen.findByText('Quero mais internet');

    const campo = screen.getByRole('textbox');
    await user.type(campo, 'Já estou vendo seu caso');
    await user.click(screen.getByRole('button', { name: /Enviar resposta/i }));

    await waitFor(() => expect(mocked.replyAsAgent)
      .toHaveBeenCalledWith('conv1', 'Já estou vendo seu caso'));
  });

  it('mostra o erro quando o envio falha', async () => {
    const user = userEvent.setup();
    mocked.replyAsAgent.mockRejectedValue(new Error('Conversa encerrada'));
    renderConversation();
    await screen.findByText('Quero mais internet');

    await user.type(screen.getByRole('textbox'), 'oi');
    await user.click(screen.getByRole('button', { name: /Enviar resposta/i }));

    expect(await screen.findByText('Conversa encerrada')).toBeInTheDocument();
  });

  it('leva ao contexto do cliente', async () => {
    renderConversation();

    const link = await screen.findByRole('link', { name: /contexto/i });
    expect(link).toHaveAttribute('href', '/console/customer-context/cus1');
  });

  it('mostra a troca de canal quando houve uma', async () => {
    mocked.getConversation.mockResolvedValue({
      ...fixtures.conversationDetail, channels_used: ['whatsapp', 'app'],
    });

    renderConversation();

    expect(await screen.findAllByText(/App Claro/)).not.toHaveLength(0);
  });
});

describe('encerramento pelo atendente', () => {
  function renderConversation() {
    return renderAt(<Conversation />, {
      path: '/console/conversation/:id', route: '/console/conversation/conv1',
    });
  }

  beforeEach(() => {
    mocked.closeConversation.mockResolvedValue({
      conversation: { ...fixtures.conversationItem, status: 'pending', closed_by: 'Admin CX' },
      survey_sent: true,
      survey_message: 'Antes de encerrar, Maria: de 0 a 10, o quanto você recomendaria '
                    + 'a Claro para um amigo ou familiar?',
    });
  });

  it('oferece encerrar o atendimento', async () => {
    renderConversation();

    expect(await screen.findByRole('button', { name: /Encerrar atendimento/ }))
      .toBeEnabled();
  });

  it('encerra e mostra a pesquisa que foi enviada ao cliente', async () => {
    const user = userEvent.setup();
    renderConversation();

    await user.click(await screen.findByRole('button', { name: /Encerrar atendimento/ }));

    await waitFor(() => expect(mocked.closeConversation)
      .toHaveBeenCalledWith('conv1', 'Admin CX'));
    expect(await screen.findByText(/Pesquisa de satisfação enviada/)).toBeInTheDocument();
    expect(screen.getByText(/0 a 10/)).toBeInTheDocument();
  });

  it('não deixa encerrar duas vezes', async () => {
    mocked.getConversation.mockResolvedValue({
      ...fixtures.conversationDetail, status: 'pending',
    });

    renderConversation();

    expect(await screen.findByRole('button', { name: /Encerrada/ })).toBeDisabled();
  });

  it('mostra o erro quando o encerramento falha', async () => {
    const user = userEvent.setup();
    mocked.closeConversation.mockRejectedValue(new Error('Conversa não encontrada'));
    renderConversation();

    await user.click(await screen.findByRole('button', { name: /Encerrar atendimento/ }));

    expect(await screen.findByText('Conversa não encontrada')).toBeInTheDocument();
  });
});

// ======================================================= contexto do cliente
describe('contexto do cliente', () => {
  function renderContext() {
    return renderAt(<CustomerContext />, {
      path: '/console/customer-context/:id', route: '/console/customer-context/cus1',
    });
  }

  it('mostra o plano e o consumo', async () => {
    renderContext();

    expect(await screen.findAllByText('Claro Flex 30GB')).not.toHaveLength(0);
    expect(screen.getAllByText('Maria Silva Santos')).not.toHaveLength(0);
    expect(screen.getByRole('progressbar', { name: /Consumo da franquia/ }))
      .toHaveAttribute('aria-valuenow', '92');
  });

  it('mascara o documento do cliente', async () => {
    renderContext();

    expect(await screen.findByText(/\*\*\*\.456\.789/)).toBeInTheDocument();
  });

  it('mostra os canais por onde o cliente já passou', async () => {
    renderContext();

    await screen.findAllByText('Maria Silva Santos');
    expect(screen.getByText('Conversas').closest('div')).toHaveTextContent('2');
  });

  it('trata cliente não identificado como estado do produto, não como erro', async () => {
    mocked.getCustomerContext.mockRejectedValue(new ApiError(404, 'Cliente não encontrado'));

    renderContext();

    expect(await screen.findByText('Cliente ainda não identificado')).toBeInTheDocument();
  });
});

// ============================================== impacto da persona no studio
describe('impacto da persona', () => {
  beforeEach(() => {
    mocked.previewPersona.mockResolvedValue({
      persona_name: 'Clara',
      persona_version: 3,
      original: 'Seu plano foi alterado.',
      previews: [
        { channel_id: 'whatsapp', channel_name: 'WhatsApp', formality_label: 'Informal',
          use_emoji: true, max_length: 160, rendered: 'Oi! Seu plano foi alterado. 🎉',
          length: 30 },
        { channel_id: 'voice', channel_name: 'URA', formality_label: 'Formal',
          use_emoji: false, max_length: 20, rendered: 'Seu plano foi alterado com sucesso.',
          length: 35 },
      ],
    });
  });

  it('mostra a mesma frase reescrita por canal', async () => {
    const user = userEvent.setup();
    renderAt(<PersonaImpact version={3} />, { route: '/console/design-studio' });

    await user.click(screen.getByRole('button', { name: /Ver o efeito/ }));

    expect(await screen.findByText('Oi! Seu plano foi alterado. 🎉')).toBeInTheDocument();
    expect(screen.getByText('Seu plano foi alterado com sucesso.')).toBeInTheDocument();
  });

  it('avisa quando o texto estoura o limite do canal', async () => {
    const user = userEvent.setup();
    renderAt(<PersonaImpact version={3} />, { route: '/console/design-studio' });

    await user.click(screen.getByRole('button', { name: /Ver o efeito/ }));

    expect(await screen.findByText('35/20')).toBeInTheDocument();
    expect(screen.getByText('30/160')).toBeInTheDocument();
  });

  it('mostra a versão vigente da persona', () => {
    renderAt(<PersonaImpact version={7} />, { route: '/console/design-studio' });

    expect(screen.getByText('persona v7')).toBeInTheDocument();
  });

  it('leva de volta a uma conversa já simulada para conferir o efeito', async () => {
    renderAt(<PersonaImpact version={3} />, { route: '/console/design-studio' });

    const atalho = await screen.findByRole('link', { name: /Maria Silva Santos/ });
    expect(atalho).toHaveAttribute('href', '/simulador/cus1');
  });

  it('convida a simular quando ainda não há conversa nenhuma', async () => {
    mocked.listCustomers.mockResolvedValue([
      { ...fixtures.customerSummary, conversation_count: 0 },
    ]);

    renderAt(<PersonaImpact version={3} />, { route: '/console/design-studio' });

    expect(await screen.findByText(/Nenhuma conversa simulada ainda/)).toBeInTheDocument();
  });

  it('mostra o erro quando a prévia falha', async () => {
    const user = userEvent.setup();
    mocked.previewPersona.mockRejectedValue(new Error('Configuração inválida'));
    renderAt(<PersonaImpact version={3} />, { route: '/console/design-studio' });

    await user.click(screen.getByRole('button', { name: /Ver o efeito/ }));

    expect(await screen.findByText('Configuração inválida')).toBeInTheDocument();
  });
});

// ------------------------------------------------------------------ utilidade
describe('detalhe selecionado no inbox', () => {
  it('mostra a jornada entre canais de quem trocou de ponto de contato', async () => {
    mocked.listConversations.mockResolvedValue([
      { ...fixtures.conversationItem, channels_used: ['whatsapp', 'app'] },
    ]);

    renderAt(<Inbox />, { route: '/console/inbox' });

    expect(await screen.findAllByText(/WhatsApp/)).not.toHaveLength(0);
    expect(screen.getAllByText(/App/).length).toBeGreaterThan(0);
  });
});

// ===================================================== Sprint 4 — painel
describe('painel do atendente (sprint 4)', () => {
  function renderConversation() {
    return renderAt(<Conversation />, {
      path: '/console/conversation/:id', route: '/console/conversation/conv1',
    });
  }

  it('mostra o humor do cliente no topo do painel', async () => {
    mocked.getConversation.mockResolvedValue({
      ...fixtures.conversationDetail, sentiment: 'negative', sentiment_score: 0.2,
    });
    renderConversation();

    const status = await screen.findByRole('status', { name: /Frustrado/ });
    expect(status).toHaveTextContent(/abordagem empática/);
  });

  it('marca o humor em cada mensagem do cliente', async () => {
    renderConversation();

    expect(await screen.findByRole('img', { name: 'Sentimento detectado: neutro' }))
      .toBeInTheDocument();
  });

  it('organiza o contexto em cartões de cliente, intenção e histórico', async () => {
    renderConversation();

    expect(await screen.findByRole('region', { name: 'Cliente' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Intenção' })).toHaveTextContent('88%');
    expect(await screen.findByText('2 conversas anteriores')).toBeInTheDocument();
    expect(mocked.getConversationHistory).toHaveBeenCalledWith('cus1', 6);
  });

  it('abre a linha do tempo na aba Histórico e a transcrição no modal', async () => {
    const user = userEvent.setup();
    renderConversation();

    await user.click(await screen.findByRole('tab', { name: /Histórico/ }));
    expect(await screen.findByRole('list', { name: 'Linha do tempo de conversas' }))
      .toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /12\/08\/2026 — Suporte/ }));
    await waitFor(() => expect(mocked.getConversation).toHaveBeenCalledWith('conv0'));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
  });

  it('oferece assumir uma conversa transferida ainda sem dono', async () => {
    const user = userEvent.setup();
    mocked.getConversation.mockResolvedValue({
      ...fixtures.conversationDetail, status: 'transferred',
      ai: { ...fixtures.conversationDetail.ai,
            handover: { ...fixtures.conversationDetail.ai.handover, requested: true,
                        reason: 'Cliente pediu atendente' } },
    });
    mocked.requestHandover.mockResolvedValue(fixtures.conversationItem);
    renderConversation();

    await user.click(await screen.findByRole('button', { name: 'Assumir atendimento' }));

    await waitFor(() => expect(mocked.requestHandover)
      .toHaveBeenCalledWith('conv1', expect.any(String), 'Admin CX'));
  });

  it('mostra com quem está a conversa já assumida', async () => {
    mocked.getConversation.mockResolvedValue({
      ...fixtures.conversationDetail, status: 'transferred',
      ai: { ...fixtures.conversationDetail.ai,
            handover: { ...fixtures.conversationDetail.ai.handover, requested: true,
                        assigned_agent: 'Admin CX' } },
    });
    renderConversation();

    expect(await screen.findByRole('button', { name: 'Com você' })).toBeDisabled();
  });
});
