import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import * as fixtures from '../../../test/fixtures';
import ConfidenceBadge, { confidenceTone, normalizeConfidence } from './ConfidenceBadge';
import ConsumptionBar, { consumptionTone } from './ConsumptionBar';
import CustomerSnapshot from './CustomerSnapshot';
import NpsHistoryBadge, { categoryFor } from './NpsHistoryBadge';

describe('barra de consumo', () => {
  it.each([[0, 'ok'], [59, 'ok'], [60, 'warning'], [79, 'warning'], [80, 'critical'], [120, 'critical']])(
    '%i%% → %s', (percent, tone) => expect(consumptionTone(percent)).toBe(tone));

  it('expõe o valor para leitor de tela e mostra a situação em texto', () => {
    render(<ConsumptionBar current={22} total={30} />);

    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '73');
    expect(bar).toHaveAccessibleName(/22GB de 30GB, atenção ao consumo/);
    expect(screen.getByText('atenção ao consumo')).toBeInTheDocument();
  });

  it('não quebra com franquia zerada', () => {
    render(<ConsumptionBar current={5} total={0} />);
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  });
});

describe('selo de confiança', () => {
  it('aceita 0–1 e 0–100', () => {
    expect(normalizeConfidence(0.97)).toBe(0.97);
    expect(normalizeConfidence(97)).toBe(0.97);
  });

  it.each([[0.97, 'high'], [0.9, 'medium'], [0.7, 'medium'], [0.69, 'low']])(
    '%f → %s', (score, tone) => expect(confidenceTone(score)).toBe(tone));

  it('mostra o ✓ só acima de 90%', () => {
    const { rerender, container } = render(<ConfidenceBadge score={0.97} />);
    expect(screen.getByText('97%')).toBeInTheDocument();
    expect(container.querySelector('svg')).not.toBeNull();

    rerender(<ConfidenceBadge score={0.8} />);
    expect(container.querySelector('svg')).toBeNull();
  });

  it('trata confiança ausente', () => {
    render(<ConfidenceBadge score={null} />);
    expect(screen.getByText('sem classificação')).toBeInTheDocument();
  });
});

describe('selo de NPS anterior', () => {
  it('usa as faixas do NPS', () => {
    expect(categoryFor(6)).toBe('detrator');
    expect(categoryFor(7)).toBe('neutro');
    expect(categoryFor(9)).toBe('promotor');
  });

  it('escreve a nota com a categoria', () => {
    render(<NpsHistoryBadge score={7} />);
    expect(screen.getByText('7 (Neutro)')).toBeInTheDocument();
  });

  it('diz quando não há nota', () => {
    render(<NpsHistoryBadge score={null} />);
    expect(screen.getByText('Sem nota registrada')).toBeInTheDocument();
  });
});

describe('cartões de contexto', () => {
  it('mostra cliente, intenção e histórico', () => {
    render(<CustomerSnapshot customer={fixtures.customerContext} intent={fixtures.intent}
                             history={fixtures.conversationHistory}
                             currentConversationId="conv1" />);

    expect(screen.getByRole('region', { name: 'Cliente' })).toHaveTextContent('Claro Flex 30GB');
    expect(screen.getByRole('region', { name: 'Intenção' })).toHaveTextContent('Alteração de Plano');
    expect(screen.getByRole('region', { name: 'Intenção' })).toHaveTextContent('88%');
    const historico = screen.getByRole('region', { name: 'Histórico' });
    expect(historico).toHaveTextContent('2 conversas anteriores');   // exclui a atual
    expect(historico).toHaveTextContent('9 (Promotor)');
  });

  it('degrada com elegância quando faltam dados', () => {
    render(<CustomerSnapshot customer={{ ...fixtures.customerContext, plan: null }}
                             intent={null} history={fixtures.emptyHistory} />);

    expect(screen.getByText('Sem plano móvel cadastrado.')).toBeInTheDocument();
    expect(screen.getByText(/Ainda sem intenção identificada/)).toBeInTheDocument();
    expect(screen.getByText(/Primeiro contato deste cliente/)).toBeInTheDocument();
  });

  it('avisa quando o cliente não está identificado', () => {
    render(<CustomerSnapshot customer={null} customerError="Cliente não encontrado"
                             intent={null} history={null} />);
    expect(screen.getByText(/Cliente ainda não identificado/)).toBeInTheDocument();
  });

  it('em linha usa três colunas no desktop e uma no celular', () => {
    render(<CustomerSnapshot layout="row" customer={fixtures.customerContext}
                             history={fixtures.conversationHistory} />);

    const grid = screen.getByTestId('customer-snapshot');
    expect(grid.className).toContain('grid-cols-1');
    expect(grid.className).toContain('md:grid-cols-3');
    expect(screen.getByRole('region', { name: 'Último atendimento' }))
      .toHaveTextContent('Alteração de Plano');
  });
});
