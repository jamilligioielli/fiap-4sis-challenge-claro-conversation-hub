import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api, ApiError } from '../../api/client';
import * as fixtures from '../../../test/fixtures';
import { renderAt } from '../../../test/render';
import DesignStudio from './DesignStudio';
import type { ChannelConfig, StudioConfig } from '../../api/types';

vi.mock('../../api/client', () => ({
  api: {
    getStudioConfig: vi.fn(),
    saveStudioConfig: vi.fn(),
    saveChannelConfig: vi.fn(),
    previewPersona: vi.fn(),
    listCustomers: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string) { super(message); }
  },
}));

const mocked = vi.mocked(api);

const channel = (id: string, name: string, voice = false): ChannelConfig => ({
  id, name,
  formalityLevel: voice ? 70 : 30,
  greeting: 'Oi, {nome}!',
  maxLength: voice ? 400 : 160,
  useEmoji: !voice,
  guidelines: ['Mensagens curtas'],
  sampleMessage: 'Oi, Maria! Posso te ajudar?',
  presentation: { color: 'text-green-600', bgColor: 'bg-green-50',
                  iconColor: 'bg-green-50' },
  voiceConfig: voice ? {
    speechRate: 50, voiceGender: 'feminino', vocabularyLevel: 40,
    captureMode: 'hybrid', menuPattern: 'option-key', maxMenuOptions: 5,
    autoRepeatTimeout: 8, maxAttempts: 3, silenceTimeout: 3000,
    transferTriggers: ['Cliente pede atendente'],
    queueMessage: 'Aguarde, por favor.',
    scriptOpening: 'Olá, {nome}! Você ligou para a Claro.',
    scriptMenu: 'Para plano, pressione 1.',
    scriptFarewell: 'Obrigada por ligar.',
    pronunciationGlossary: [{ term: 'Wi-Fi', pronunciation: 'Uai-Fai' }],
  } : null,
});

const config: StudioConfig = {
  ...fixtures.studioConfig,
  persona: { name: 'Clara', description: 'Assistente da Claro',
             traits: ['clara', 'direta', 'resolutiva'] },
  intents: [{ slug: 'alteracao_plano', name: 'Alteração de Plano',
              confidence: 'Alta', examples: 'quero mudar de plano' }],
  guardrails: [{ rule: 'Nunca prometer o que não pode cumprir', category: 'Ética' }],
  channels: [channel('whatsapp', 'WhatsApp'), channel('webchat', 'Web Chat'),
             channel('app', 'App Claro'), channel('voice', 'URA — Voz', true)],
};

beforeEach(() => {
  vi.clearAllMocks();
  mocked.getStudioConfig.mockResolvedValue(config);
  mocked.saveStudioConfig.mockResolvedValue({ ...config, version: config.version + 1 });
  mocked.saveChannelConfig.mockResolvedValue({ ...config, version: config.version + 1 });
  mocked.listCustomers.mockResolvedValue([fixtures.customerSummary]);
  mocked.previewPersona.mockResolvedValue({
    persona_name: 'Clara', persona_version: 3, original: 'oi', previews: [],
  });
});

function render() {
  return renderAt(<DesignStudio />, { route: '/console/design-studio' });
}

describe('configuração da persona', () => {
  it('mostra quem é a Clara e o que a define', async () => {
    render();

    expect(await screen.findByDisplayValue('Clara')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Assistente da Claro')).toBeInTheDocument();
    expect(screen.getByText('resolutiva')).toBeInTheDocument();
  });

  it('lista os guardrails com a categoria de cada um', async () => {
    render();

    expect(await screen.findByText('Nunca prometer o que não pode cumprir'))
      .toBeInTheDocument();
    expect(screen.getByText('Ética')).toBeInTheDocument();
  });

  it('salva a persona editada', async () => {
    const user = userEvent.setup();
    render();
    const nome = await screen.findByDisplayValue('Clara');

    await user.clear(nome);
    await user.type(nome, 'Clarice');
    await user.click(screen.getByRole('button', { name: /Salvar Alterações/ }));

    await waitFor(() => expect(mocked.saveStudioConfig).toHaveBeenCalledWith(
      expect.objectContaining({
        persona: expect.objectContaining({ name: 'Clarice' }),
      })));
  });

  it('mostra o erro quando a gravação falha', async () => {
    const user = userEvent.setup();
    mocked.saveStudioConfig.mockRejectedValue(new Error('Configuração inválida'));
    render();
    await screen.findByDisplayValue('Clara');

    await user.click(screen.getByRole('button', { name: /Salvar Alterações/ }));

    expect(await screen.findByText('Configuração inválida')).toBeInTheDocument();
  });
});

describe('canais', () => {
  it('lista os quatro canais com o tom de cada um', async () => {
    render();

    expect(await screen.findByText('WhatsApp')).toBeInTheDocument();
    expect(screen.getByText('Web Chat')).toBeInTheDocument();
    expect(screen.getByText('App Claro')).toBeInTheDocument();
    expect(screen.getByText('URA — Voz')).toBeInTheDocument();
  });

  it('abre o editor do canal escolhido', async () => {
    const user = userEvent.setup();
    render();

    await user.click(await screen.findByText('WhatsApp'));

    expect(await screen.findByText(/Voltar ao Design Studio/)).toBeInTheDocument();
  });

  it('a URA tem um editor próprio, com script e transbordo', async () => {
    const user = userEvent.setup();
    render();

    await user.click(await screen.findByText('URA — Voz'));

    expect(await screen.findByText(/Script da URA/)).toBeInTheDocument();
    expect(screen.getByText(/Transbordo/)).toBeInTheDocument();
  });

  it('grava apenas o canal editado', async () => {
    const user = userEvent.setup();
    render();
    await user.click(await screen.findByText('WhatsApp'));

    await user.click(await screen.findByRole('button', { name: /Salvar/ }));

    await waitFor(() => expect(mocked.saveChannelConfig)
      .toHaveBeenCalledWith('whatsapp', expect.objectContaining({ maxLength: 160 })));
  });
});

describe('efeito da configuração', () => {
  it('oferece a conferência do efeito dentro da conversa', async () => {
    render();

    expect(await screen.findByText('O que muda na conversa')).toBeInTheDocument();
    expect(screen.getByText(`persona v${config.version}`)).toBeInTheDocument();
  });

  it('não mostra mais o banner decorativo que não provava nada', async () => {
    render();

    await screen.findByText('O que muda na conversa');
    expect(screen.queryByText(/expressão da identidade conversacional/))
      .not.toBeInTheDocument();
  });
});

describe('falha de carregamento', () => {
  it('explica quando a configuração não carrega', async () => {
    mocked.getStudioConfig.mockRejectedValue(
      new ApiError(0, 'Não foi possível alcançar a API do hub.'));

    render();

    expect(await screen.findByText(/API do hub indisponível/)).toBeInTheDocument();
  });
});
