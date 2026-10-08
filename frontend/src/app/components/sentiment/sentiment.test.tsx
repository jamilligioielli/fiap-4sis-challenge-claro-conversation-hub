import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import MessageSentimentBadge from './MessageSentimentBadge';
import SentimentIndicator from './SentimentIndicator';

describe('indicador de sentimento', () => {
  it('cliente frustrado pede abordagem empática', () => {
    render(<SentimentIndicator sentiment="negative" score={0.22} />);

    const status = screen.getByRole('status', { name: /Frustrado/ });
    expect(status).toHaveTextContent('😠');
    expect(status).toHaveTextContent(/abordagem empática recomendada/);
    expect(status).toHaveTextContent('índice 22/100');
  });

  it('cliente calmo e neutro', () => {
    const { rerender } = render(<SentimentIndicator sentiment="positive" score={0.8} />);
    expect(screen.getByRole('status')).toHaveTextContent('Calmo');

    rerender(<SentimentIndicator sentiment="neutral" score={0.5} />);
    expect(screen.getByRole('status')).toHaveTextContent('Neutro');
  });

  it('antes da primeira mensagem não inventa humor', () => {
    render(<SentimentIndicator sentiment={null} />);
    expect(screen.getByText(/ainda não detectado/)).toBeInTheDocument();
  });

  it('selo da mensagem tem o humor no tooltip e para leitor de tela', () => {
    render(<MessageSentimentBadge sentiment="negative" />);
    const badge = screen.getByRole('img', { name: 'Sentimento detectado: negativo' });
    expect(badge).toHaveAttribute('title', 'Sentimento detectado: negativo');
  });
});
