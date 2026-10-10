import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../../api/client';
import type { ConversationListItem } from '../../api/types';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import ConversationInboxForAgent from './ConversationInboxForAgent';

vi.mock('../../api/client', () => ({
  api: { listAgentQueue: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

function transferred(id: string, name: string, minutesAgo: number,
                     extra: Partial<ConversationListItem> = {}): ConversationListItem {
  return {
    ...fixtures.conversationItem,
    id, customer_name: name, status: 'transferred', priority: 'high',
    handover_requested: true, attended_by: 'agent',
    handover_requested_at: new Date(Date.now() - minutesAgo * 60000).toISOString(),
    waiting_seconds: minutesAgo * 60, message_count: 6,
    ...extra,
  };
}

const queue = [
  transferred('c1', 'Felipe Barros', 42, { unread: true, sentiment: 'negative' }),
  transferred('c2', 'Carla Mendes', 8, { assigned_agent: 'Admin CX' }),
  transferred('c3', 'João Santos', 2, { priority: 'medium' }),
];

beforeEach(() => {
  vi.clearAllMocks();
  mocked.listAgentQueue.mockResolvedValue(queue);
});

describe('inbox do atendente', () => {
  it('pede à API só as transferidas para o atendente, por prioridade', async () => {
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });

    await screen.findByText('Felipe Barros');
    expect(mocked.listAgentQueue).toHaveBeenCalledWith({ agent: 'Admin CX', sortBy: 'priority' });
  });

  it('mantém a ordem da API e numera a fila', async () => {
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });

    const fila = await screen.findByRole('list', { name: 'Fila do atendente' });
    const itens = within(fila).getAllByRole('link');
    expect(itens[0]).toHaveAccessibleName(/1º na fila: Felipe Barros/);
    expect(itens[2]).toHaveAccessibleName(/3º na fila: João Santos/);
    expect(screen.getByText('3 conversas aguardando')).toBeInTheDocument();
  });

  it('mostra tempo de espera e urgência em texto, não só em cor', async () => {
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });

    const felipe = (await screen.findByText('Felipe Barros')).closest('a')!;
    expect(felipe).toHaveTextContent('42 min');
    expect(felipe).toHaveTextContent('Crítico');
    expect(felipe).toHaveTextContent('Frustrado');
    const carla = screen.getByText('Carla Mendes').closest('a')!;
    expect(carla).toHaveTextContent('Atenção');
    expect(carla).toHaveTextContent('Com você');
  });

  it('desligar "apenas para mim" busca todas as transferidas', async () => {
    const user = userEvent.setup();
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });
    await screen.findByText('Felipe Barros');

    await user.click(screen.getByRole('switch', { name: /apenas transferidas para mim/ }));

    await waitFor(() => expect(mocked.listAgentQueue)
      .toHaveBeenLastCalledWith({ agent: undefined, sortBy: 'priority' }));
  });

  it('troca a ordenação', async () => {
    const user = userEvent.setup();
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });
    await screen.findByText('Felipe Barros');

    await user.selectOptions(screen.getByRole('combobox', { name: 'Ordenar por' }), 'wait_time');

    await waitFor(() => expect(mocked.listAgentQueue)
      .toHaveBeenLastCalledWith({ agent: 'Admin CX', sortBy: 'wait_time' }));
  });

  it('filtra as que aguardam resposta', async () => {
    const user = userEvent.setup();
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });
    await screen.findByText('Felipe Barros');

    await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'awaiting');

    expect(screen.getByText('1 conversa aguardando')).toBeInTheDocument();
    expect(screen.queryByText('Carla Mendes')).not.toBeInTheDocument();
  });

  it('leva à conversa ao clicar', async () => {
    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });

    const link = (await screen.findByText('Felipe Barros')).closest('a');
    expect(link).toHaveAttribute('href', '/console/conversation/c1');
  });

  it('explica a fila vazia', async () => {
    mocked.listAgentQueue.mockResolvedValue([]);

    renderAt(<ConversationInboxForAgent />, { route: '/console/inbox-atendente' });

    expect(await screen.findByText('Nenhuma conversa na sua fila')).toBeInTheDocument();
  });
});
