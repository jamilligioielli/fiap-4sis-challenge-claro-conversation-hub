import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import ConversationHistoryModal from './ConversationHistoryModal';
import ConversationTimeline from './ConversationTimeline';
import ConversationTimelineInsights from './ConversationTimelineInsights';
import { formatDate } from './historyStyles';

vi.mock('../../api/client', () => ({
  api: { getConversation: vi.fn() },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);
beforeEach(() => vi.clearAllMocks());

describe('linha do tempo', () => {
  it('mostra cada conversa com data, tipo, situação e nota', () => {
    render(<ConversationTimeline items={fixtures.conversationHistory.items} onSelect={() => {}} />);

    const itens = within(screen.getByRole('list', { name: 'Linha do tempo de conversas' }))
      .getAllByRole('listitem');
    expect(itens).toHaveLength(3);
    expect(itens[0]).toHaveTextContent('30/08');
    expect(itens[0]).toHaveTextContent('atual');
    expect(itens[0]).toHaveTextContent('Em andamento');
    expect(itens[1]).toHaveTextContent('Resolvida');
    expect(itens[1]).toHaveTextContent('9 (Promotor)');
    expect(itens[2]).toHaveTextContent('Encerrada com insatisfação');
  });

  it('avisa quando é o primeiro contato', () => {
    render(<ConversationTimeline items={[]} onSelect={() => {}} />);
    expect(screen.getByText(/Primeiro contato deste cliente/)).toBeInTheDocument();
  });

  it('clicar num ponto pede a transcrição daquela conversa', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<ConversationTimeline items={fixtures.conversationHistory.items} onSelect={onSelect} />);

    await user.click(screen.getByRole('button', { name: /12\/08\/2026 — Suporte/ }));

    expect(onSelect).toHaveBeenCalledWith(fixtures.conversationHistory.items[1]);
  });

  it('formata datas no padrão brasileiro', () => {
    expect(formatDate('2026-10-05')).toBe('05/10/2026');
    expect(formatDate('2026-10-05', true)).toBe('05/10');
  });
});

describe('indicadores do histórico', () => {
  it('resume frequência, assunto, NPS e resolução', () => {
    render(<ConversationTimelineInsights insights={fixtures.conversationHistory.insights}
                                         months={6} />);

    const painel = screen.getByRole('region', { name: 'Indicadores do histórico' });
    expect(painel).toHaveTextContent('A cada 20,5 dias');
    expect(painel).toHaveTextContent('Suporte');
    expect(painel).toHaveTextContent('6,5 (Detrator)');
    expect(painel).toHaveTextContent('50%');
  });

  it('não aparece sem conversas', () => {
    const { container } = render(
      <ConversationTimelineInsights insights={fixtures.emptyHistory.insights} months={6} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('transcrição em modal', () => {
  it('abre com a conversa escolhida e fecha', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    mocked.getConversation.mockResolvedValue(fixtures.conversationDetail);

    render(<ConversationHistoryModal item={fixtures.conversationHistory.items[1]}
                                     onClose={onClose} />);

    expect(await screen.findByText('Quero mais internet')).toBeInTheDocument();
    expect(mocked.getConversation).toHaveBeenCalledWith('conv0');
    expect(screen.getByRole('dialog')).toHaveTextContent('Suporte · 12/08/2026');

    await user.click(screen.getByRole('button', { name: 'Fechar' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('fica fechado sem conversa escolhida', () => {
    render(<ConversationHistoryModal item={null} onClose={() => {}} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
