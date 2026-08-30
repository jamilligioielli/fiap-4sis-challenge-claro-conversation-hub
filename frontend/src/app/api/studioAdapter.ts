/**
 * Adaptador entre a configuração da API e a forma que a tela do Design Studio usa.
 *
 * O domínio separou apresentação de regra de negócio: as classes de cor viraram
 * `presentation` e `maxLength` virou número. A tela, herdada do protótipo,
 * trabalha com os campos achatados e `maxLength` como string (é o que um
 * `<input>` devolve).
 *
 * Traduzir nas bordas — e não forçar um dos lados a ceder — é o que mantém o
 * back-end limpo sem exigir a reescrita de mil linhas de interface.
 */
import type { ChannelConfig as ApiChannel, StudioConfig, VoiceConfig } from './types';

export interface UiChannelConfig {
  id: string;
  name: string;
  formalityLevel: number;
  greeting: string;
  maxLength: string;
  useEmoji: boolean;
  guidelines: string[];
  sampleMessage: string;
  color: string;
  bgColor: string;
  iconColor: string;
  voiceConfig?: VoiceConfig;
}

export function toUiChannel(channel: ApiChannel): UiChannelConfig {
  return {
    id: channel.id,
    name: channel.name,
    formalityLevel: channel.formalityLevel,
    greeting: channel.greeting,
    maxLength: String(channel.maxLength),
    useEmoji: channel.useEmoji,
    guidelines: channel.guidelines,
    sampleMessage: channel.sampleMessage,
    color: channel.presentation?.color ?? '',
    bgColor: channel.presentation?.bgColor ?? '',
    iconColor: channel.presentation?.iconColor ?? '',
    voiceConfig: channel.voiceConfig ?? undefined,
  };
}

/** Só os campos que a tela edita — a apresentação não volta para a API. */
export function toApiPatch(channel: UiChannelConfig): Record<string, unknown> {
  const parsed = Number.parseInt(channel.maxLength, 10);
  return {
    formalityLevel: channel.formalityLevel,
    greeting: channel.greeting,
    maxLength: Number.isFinite(parsed) && parsed > 0 ? parsed : 280,
    useEmoji: channel.useEmoji,
    guidelines: channel.guidelines,
    sampleMessage: channel.sampleMessage,
    ...(channel.voiceConfig ? { voiceConfig: channel.voiceConfig } : {}),
  };
}

export function toUiChannels(config: StudioConfig): UiChannelConfig[] {
  return config.channels.map(toUiChannel);
}
