import { describe, expect, it } from 'vitest';

import { toApiPatch, toUiChannel, toUiChannels } from './studioAdapter';
import type { ChannelConfig, StudioConfig } from './types';

/**
 * O adaptador é a fronteira entre dois vocabulários.
 *
 * A API modela `maxLength` como número e a apresentação como objeto; a tela,
 * herdada do protótipo, usa string e campos achatados — porque é isso que um
 * `<input>` devolve. O erro que este teste previne é silencioso: um `maxLength`
 * que chega como `"160"` numa API que espera `160` passa pelo TypeScript e
 * quebra na hora da gravação.
 */

const apiChannel: ChannelConfig = {
  id: 'whatsapp',
  name: 'WhatsApp',
  formalityLevel: 30,
  greeting: 'Oi, {nome}! 👋',
  maxLength: 160,
  useEmoji: true,
  guidelines: ['Mensagens curtas'],
  sampleMessage: 'Oi, Maria! Posso te ajudar?',
  presentation: { color: 'text-green-600', bgColor: 'bg-green-50',
                  iconColor: 'bg-green-50' },
  voiceConfig: null,
};

describe('da API para a tela', () => {
  it('achata a apresentação em campos separados', () => {
    const ui = toUiChannel(apiChannel);

    expect(ui.color).toBe('text-green-600');
    expect(ui.bgColor).toBe('bg-green-50');
  });

  it('converte o limite de caracteres para o que o input entende', () => {
    expect(toUiChannel(apiChannel).maxLength).toBe('160');
  });

  it('sobrevive a um canal sem apresentação definida', () => {
    const ui = toUiChannel({ ...apiChannel, presentation: undefined as never });

    expect(ui.color).toBe('');
    expect(ui.bgColor).toBe('');
  });

  it('converte a lista inteira de canais', () => {
    const config = { channels: [apiChannel, { ...apiChannel, id: 'app' }] } as StudioConfig;

    expect(toUiChannels(config).map((c) => c.id)).toEqual(['whatsapp', 'app']);
  });
});

describe('da tela para a API', () => {
  it('devolve o limite como número', () => {
    const patch = toApiPatch(toUiChannel(apiChannel));

    expect(patch.maxLength).toBe(160);
    expect(typeof patch.maxLength).toBe('number');
  });

  it('usa um limite seguro quando o campo fica vazio ou inválido', () => {
    const vazio = toApiPatch({ ...toUiChannel(apiChannel), maxLength: '' });
    const texto = toApiPatch({ ...toUiChannel(apiChannel), maxLength: 'abc' });
    const zero = toApiPatch({ ...toUiChannel(apiChannel), maxLength: '0' });

    expect(vazio.maxLength).toBe(280);
    expect(texto.maxLength).toBe(280);
    expect(zero.maxLength).toBe(280);
  });

  it('não devolve a apresentação para a API', () => {
    const patch = toApiPatch(toUiChannel(apiChannel));

    expect(patch).not.toHaveProperty('color');
    expect(patch).not.toHaveProperty('bgColor');
    expect(patch).not.toHaveProperty('id');
  });

  it('só inclui a configuração de voz quando ela existe', () => {
    const semVoz = toApiPatch(toUiChannel(apiChannel));
    const comVoz = toApiPatch({
      ...toUiChannel(apiChannel),
      voiceConfig: { speechRate: 50 } as never,
    });

    expect(semVoz).not.toHaveProperty('voiceConfig');
    expect(comVoz.voiceConfig).toEqual({ speechRate: 50 });
  });

  it('preserva o que a tela realmente edita', () => {
    const patch = toApiPatch({ ...toUiChannel(apiChannel), useEmoji: false,
                               greeting: 'Bom dia, {nome}.' });

    expect(patch.useEmoji).toBe(false);
    expect(patch.greeting).toBe('Bom dia, {nome}.');
    expect(patch.formalityLevel).toBe(30);
  });
});
