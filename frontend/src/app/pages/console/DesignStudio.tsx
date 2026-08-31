import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import { useStudioConfig } from '../../api/hooks';
import { toApiPatch, toUiChannels } from '../../api/studioAdapter';
import { AsyncBoundary } from '../../components/AsyncBoundary';
import PersonaImpact from './PersonaImpact';
import type { StudioConfig } from '../../api/types';
import {
  User, MessageSquare, Shield, Globe, Code2, CheckCircle,
  ChevronRight, ArrowLeft, Plus, Trash2, Edit3, Save, Smartphone, Phone,
  Volume2, FileText, LayoutList, GitBranch, BookOpen, Mic, PhoneForwarded,
} from 'lucide-react';
import { cn } from '../../components/ui/utils';

// ─── Types ───────────────────────────────────────────────────────────────────

interface VoiceConfig {
  speechRate: number;
  voiceGender: 'feminino' | 'masculino';
  vocabularyLevel: number;
  captureMode: 'dtmf' | 'voice' | 'hybrid';
  menuPattern: 'option-key' | 'key-option';
  maxMenuOptions: number;
  autoRepeatTimeout: number;
  maxAttempts: number;
  silenceTimeout: number;
  transferTriggers: string[];
  queueMessage: string;
  scriptOpening: string;
  scriptMenu: string;
  scriptFarewell: string;
  pronunciationGlossary: { term: string; pronunciation: string }[];
}

interface ChannelConfig {
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

// ─── Defaults ────────────────────────────────────────────────────────────────

const defaultVoiceConfig: VoiceConfig = {
  speechRate: 50,
  voiceGender: 'feminino',
  vocabularyLevel: 40,
  captureMode: 'hybrid',
  menuPattern: 'option-key',
  maxMenuOptions: 5,
  autoRepeatTimeout: 8,
  maxAttempts: 3,
  silenceTimeout: 3000,
  transferTriggers: [
    'Cliente solicita falar com atendente',
    'Falha de reconhecimento após 3 tentativas',
    'Intent de insatisfação detectada',
    'Assunto fora do escopo da URA',
  ],
  queueMessage: 'Por favor, aguarde. Você será atendido em instantes. Sua ligação é muito importante para nós.',
  scriptOpening: 'Olá, {nome}! Você ligou para a Claro. Sou a Clara, sua assistente virtual. Para continuar, precisarei verificar sua identidade.',
  scriptMenu: 'Você pode dizer o que precisa ou pressionar uma das opções. Para alteração de plano, pressione 1. Para segunda via de fatura, pressione 2. Para suporte técnico, pressione 3. Para falar com um atendente, pressione 0.',
  scriptFarewell: 'Obrigada por entrar em contato com a Claro, {nome}. Seu atendimento foi encerrado. Tenha um ótimo dia!',
  pronunciationGlossary: [
    { term: 'Claro', pronunciation: 'Claro' },
    { term: 'PIX', pronunciation: 'Pix' },
    { term: 'CPF', pronunciation: 'C, P, F' },
    { term: 'URA', pronunciation: 'U, R, A' },
    { term: 'Wi-Fi', pronunciation: 'Uai-Fai' },
    { term: 'SMS', pronunciation: 'S, M, S' },
  ],
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getChannelIcon(id: string) {
  switch (id) {
    case 'whatsapp': return MessageSquare;
    case 'webchat': return Globe;
    case 'app': return Smartphone;
    case 'voice': return Phone;
    default: return MessageSquare;
  }
}

function formalityLabel(val: number) {
  if (val < 25) return 'Muito Informal';
  if (val < 45) return 'Informal';
  if (val < 60) return 'Equilibrado';
  if (val < 80) return 'Formal';
  return 'Muito Formal';
}

function speechRateLabel(val: number) {
  if (val < 25) return 'Muito Lenta';
  if (val < 45) return 'Lenta';
  if (val < 60) return 'Normal';
  if (val < 80) return 'Rápida';
  return 'Muito Rápida';
}

function vocabularyLabel(val: number) {
  if (val < 35) return 'Simples';
  if (val < 65) return 'Moderado';
  return 'Técnico';
}

// ─── Toggle helper ────────────────────────────────────────────────────────────

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={cn('w-11 h-6 rounded-full relative transition-colors duration-200 flex-shrink-0', on ? 'bg-[#E10019]' : 'bg-gray-200')}
    >
      <span className={cn('absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200', on ? 'left-5' : 'left-0.5')} />
    </button>
  );
}

// ─── Voice / URA Channel Editor ───────────────────────────────────────────────

type VoiceTab = 'tts' | 'script' | 'menus' | 'transbordo' | 'glossario';

const voiceTabs: { id: VoiceTab; label: string; icon: typeof Volume2 }[] = [
  { id: 'tts', label: 'Voz & TTS', icon: Volume2 },
  { id: 'script', label: 'Script da URA', icon: FileText },
  { id: 'menus', label: 'Menus & Captura', icon: LayoutList },
  { id: 'transbordo', label: 'Transbordo', icon: PhoneForwarded },
  { id: 'glossario', label: 'Glossário', icon: BookOpen },
];

function VoiceChannelEditor({
  channel,
  onSave,
  onBack,
}: {
  channel: ChannelConfig;
  onSave: (updated: ChannelConfig) => void;
  onBack: () => void;
}) {
  const [vc, setVc] = useState<VoiceConfig>({ ...(channel.voiceConfig ?? defaultVoiceConfig) });
  const [tab, setTab] = useState<VoiceTab>('tts');
  const [newTrigger, setNewTrigger] = useState('');
  const [newGlossaryTerm, setNewGlossaryTerm] = useState('');
  const [newGlossaryPron, setNewGlossaryPron] = useState('');

  const save = () => onSave({ ...channel, voiceConfig: vc });

  const addTrigger = () => {
    if (!newTrigger.trim()) return;
    setVc({ ...vc, transferTriggers: [...vc.transferTriggers, newTrigger.trim()] });
    setNewTrigger('');
  };

  const removeTrigger = (i: number) =>
    setVc({ ...vc, transferTriggers: vc.transferTriggers.filter((_, idx) => idx !== i) });

  const addGlossaryRow = () => {
    if (!newGlossaryTerm.trim()) return;
    setVc({ ...vc, pronunciationGlossary: [...vc.pronunciationGlossary, { term: newGlossaryTerm.trim(), pronunciation: newGlossaryPron.trim() }] });
    setNewGlossaryTerm('');
    setNewGlossaryPron('');
  };

  const removeGlossaryRow = (i: number) =>
    setVc({ ...vc, pronunciationGlossary: vc.pronunciationGlossary.filter((_, idx) => idx !== i) });

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-5xl mx-auto p-6">
        {/* Back */}
        <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Voltar ao Design Studio
        </button>

        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 rounded-xl bg-purple-50 flex items-center justify-center">
            <Phone className="w-6 h-6 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">URA — Voz (IVR)</h1>
            <p className="text-sm text-gray-500 mt-0.5">Configurações de linguagem e comportamento da Unidade de Resposta Audível</p>
          </div>
          <button
            onClick={save}
            className="ml-auto flex items-center gap-2 px-5 py-2.5 bg-[#E10019] text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            <Save className="w-4 h-4" />
            Salvar Configurações
          </button>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 bg-white border border-gray-200 rounded-xl p-1 mb-6 overflow-x-auto">
          {voiceTabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                tab === id ? 'bg-[#E10019] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* ── Tab: Voz & TTS ── */}
        {tab === 'tts' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-5">Síntese de Voz (TTS)</h2>
              <div className="space-y-6">
                {/* Gender */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-3 block">Gênero da Voz</label>
                  <div className="flex gap-3">
                    {(['feminino', 'masculino'] as const).map((g) => (
                      <button
                        key={g}
                        onClick={() => setVc({ ...vc, voiceGender: g })}
                        className={cn(
                          'flex-1 py-2.5 rounded-lg text-sm font-medium border transition-colors capitalize',
                          vc.voiceGender === g
                            ? 'bg-purple-50 border-purple-300 text-purple-700'
                            : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                        )}
                      >
                        {g.charAt(0).toUpperCase() + g.slice(1)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Speech rate */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-3 block">
                    Velocidade de Fala —{' '}
                    <span className="font-semibold text-gray-900">{speechRateLabel(vc.speechRate)}</span>
                  </label>
                  <input
                    type="range" min={0} max={100} value={vc.speechRate}
                    onChange={(e) => setVc({ ...vc, speechRate: Number(e.target.value) })}
                    className="w-full accent-purple-600"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>Muito Lenta</span>
                    <span>Normal</span>
                    <span>Muito Rápida</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">Velocidades mais lentas melhoram compreensão para clientes idosos</p>
                </div>

                {/* Vocabulary */}
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-3 block">
                    Complexidade do Vocabulário —{' '}
                    <span className="font-semibold text-gray-900">{vocabularyLabel(vc.vocabularyLevel)}</span>
                  </label>
                  <input
                    type="range" min={0} max={100} value={vc.vocabularyLevel}
                    onChange={(e) => setVc({ ...vc, vocabularyLevel: Number(e.target.value) })}
                    className="w-full accent-purple-600"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>Simples</span>
                    <span>Moderado</span>
                    <span>Técnico</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Summary card */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-5">Resumo da Configuração</h2>
              <div className="space-y-3">
                {[
                  { label: 'Gênero', value: vc.voiceGender === 'feminino' ? 'Feminino' : 'Masculino' },
                  { label: 'Velocidade', value: speechRateLabel(vc.speechRate) },
                  { label: 'Vocabulário', value: vocabularyLabel(vc.vocabularyLevel) },
                  { label: 'Modo de Captura', value: vc.captureMode === 'dtmf' ? 'DTMF (Teclado)' : vc.captureMode === 'voice' ? 'Reconhecimento de Voz' : 'Híbrido' },
                  { label: 'Máx. Tentativas', value: `${vc.maxAttempts}x antes do transbordo` },
                  { label: 'Padrão de Menu', value: vc.menuPattern === 'option-key' ? '"Para X, pressione 1"' : '"Pressione 1 para X"' },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <span className="text-sm text-gray-500">{label}</span>
                    <span className="text-sm font-medium text-gray-900">{value}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 bg-purple-50 rounded-lg border border-purple-100">
                <p className="text-xs text-purple-700 font-medium mb-1">Dica de acessibilidade</p>
                <p className="text-xs text-purple-600">
                  Velocidade lenta + vocabulário simples aumenta em até 40% a taxa de conclusão para clientes acima de 60 anos.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Tab: Script da URA ── */}
        {tab === 'script' && (
          <div className="space-y-6">
            {[
              {
                key: 'scriptOpening' as const,
                label: 'Saudação / Abertura',
                hint: 'Primeira frase ao atender a ligação. Use {nome} para personalização.',
                icon: '👋',
              },
              {
                key: 'scriptMenu' as const,
                label: 'Menu Principal',
                hint: 'Apresentação das opções disponíveis. Inclua o número de cada opção.',
                icon: '📋',
              },
              {
                key: 'scriptFarewell' as const,
                label: 'Despedida / Encerramento',
                hint: 'Mensagem ao finalizar o atendimento com sucesso.',
                icon: '✅',
              },
            ].map(({ key, label, hint, icon }) => (
              <div key={key} className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{icon}</span>
                  <h2 className="text-base font-semibold text-gray-900">{label}</h2>
                </div>
                <p className="text-xs text-gray-400 mb-3">{hint}</p>
                <textarea
                  rows={4}
                  value={vc[key]}
                  onChange={(e) => setVc({ ...vc, [key]: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white transition resize-none leading-relaxed"
                />
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-gray-400">{vc[key].length} caracteres</span>
                  <span className="text-xs text-gray-400">~{Math.ceil(vc[key].length / 14)} seg. de áudio</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Tab: Menus & Captura ── */}
        {tab === 'menus' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Menu structure */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-5">Estrutura de Menu</h2>
              <div className="space-y-5">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-3 block">Padrão de Apresentação</label>
                  <div className="space-y-2">
                    {[
                      { value: 'option-key', label: '"Para [opção], pressione [tecla]"', example: 'Para segunda via, pressione 2' },
                      { value: 'key-option', label: '"Pressione [tecla] para [opção]"', example: 'Pressione 2 para segunda via' },
                    ].map(({ value, label, example }) => (
                      <button
                        key={value}
                        onClick={() => setVc({ ...vc, menuPattern: value as VoiceConfig['menuPattern'] })}
                        className={cn(
                          'w-full text-left p-3 rounded-lg border transition-colors',
                          vc.menuPattern === value
                            ? 'border-purple-300 bg-purple-50'
                            : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                        )}
                      >
                        <div className={cn('text-sm font-medium', vc.menuPattern === value ? 'text-purple-700' : 'text-gray-900')}>
                          {label}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">Ex: {example}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1.5 block">
                    Máx. de opções por menu
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="number" min={2} max={9} value={vc.maxMenuOptions}
                      onChange={(e) => setVc({ ...vc, maxMenuOptions: Number(e.target.value) })}
                      className="w-24 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white transition"
                    />
                    <p className="text-xs text-gray-400">Recomendado: até 5 opções</p>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1.5 block">Repetição automática (segundos de silêncio)</label>
                  <div className="flex items-center gap-3">
                    <input
                      type="number" min={0} max={30} value={vc.autoRepeatTimeout}
                      onChange={(e) => setVc({ ...vc, autoRepeatTimeout: Number(e.target.value) })}
                      className="w-24 px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white transition"
                    />
                    <p className="text-xs text-gray-400">0 = desativado</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Capture mode */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-5">Captura de Entrada</h2>
              <div className="space-y-5">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-3 block">Modo de Captura</label>
                  <div className="space-y-2">
                    {[
                      { value: 'dtmf', label: 'DTMF — Teclado numérico', desc: 'Cliente pressiona teclas. Mais confiável, menos natural.' },
                      { value: 'voice', label: 'Voz — Reconhecimento de fala', desc: 'Cliente fala o que precisa. Mais natural, requer ASR.' },
                      { value: 'hybrid', label: 'Híbrido — Teclado + Voz', desc: 'Aceita os dois modos. Maior flexibilidade.' },
                    ].map(({ value, label, desc }) => (
                      <button
                        key={value}
                        onClick={() => setVc({ ...vc, captureMode: value as VoiceConfig['captureMode'] })}
                        className={cn(
                          'w-full text-left p-3 rounded-lg border transition-colors',
                          vc.captureMode === value ? 'border-purple-300 bg-purple-50' : 'border-gray-200 bg-gray-50 hover:bg-gray-100'
                        )}
                      >
                        <div className={cn('text-sm font-medium', vc.captureMode === value ? 'text-purple-700' : 'text-gray-900')}>
                          {label}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">{desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1.5 block">Máx. de tentativas</label>
                    <input
                      type="number" min={1} max={5} value={vc.maxAttempts}
                      onChange={(e) => setVc({ ...vc, maxAttempts: Number(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white transition"
                    />
                    <p className="text-xs text-gray-400 mt-1">Antes do transbordo</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1.5 block">Timeout de silêncio (ms)</label>
                    <input
                      type="number" min={500} max={10000} step={500} value={vc.silenceTimeout}
                      onChange={(e) => setVc({ ...vc, silenceTimeout: Number(e.target.value) })}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white transition"
                    />
                    <p className="text-xs text-gray-400 mt-1">Espera antes de repetir</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Tab: Transbordo ── */}
        {tab === 'transbordo' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-5">
                <GitBranch className="w-5 h-5 text-orange-500" />
                <h2 className="text-base font-semibold text-gray-900">Gatilhos de Transbordo</h2>
              </div>
              <p className="text-xs text-gray-400 mb-4">Condições que acionam a transferência automática para um agente humano</p>
              <div className="space-y-2 mb-4">
                {vc.transferTriggers.map((t, i) => (
                  <div key={i} className="flex items-center gap-3 group">
                    <div className="w-2 h-2 rounded-full bg-orange-400 flex-shrink-0" />
                    <input
                      type="text" value={t}
                      onChange={(e) => {
                        const updated = [...vc.transferTriggers];
                        updated[i] = e.target.value;
                        setVc({ ...vc, transferTriggers: updated });
                      }}
                      className="flex-1 px-3 py-1.5 text-sm border border-transparent rounded-lg bg-gray-50 hover:border-gray-200 focus:outline-none focus:ring-2 focus:ring-orange-300 focus:bg-white transition"
                    />
                    <button onClick={() => removeTrigger(i)} className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <Plus className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <input
                  type="text" value={newTrigger}
                  onChange={(e) => setNewTrigger(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addTrigger()}
                  placeholder="Novo gatilho... (Enter para adicionar)"
                  className="flex-1 px-3 py-1.5 text-sm border border-dashed border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-300 focus:bg-white focus:border-solid transition"
                />
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-5">
                <Mic className="w-5 h-5 text-orange-500" />
                <h2 className="text-base font-semibold text-gray-900">Mensagem de Espera em Fila</h2>
              </div>
              <p className="text-xs text-gray-400 mb-3">Reproduzida enquanto o cliente aguarda transferência para humano</p>
              <textarea
                rows={5}
                value={vc.queueMessage}
                onChange={(e) => setVc({ ...vc, queueMessage: e.target.value })}
                className="w-full px-4 py-3 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-orange-300 focus:bg-white transition resize-none leading-relaxed"
              />
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-gray-400">{vc.queueMessage.length} caracteres</span>
                <span className="text-xs text-gray-400">~{Math.ceil(vc.queueMessage.length / 14)} seg. de áudio</span>
              </div>
              <div className="mt-4 p-3 bg-orange-50 rounded-lg border border-orange-100">
                <p className="text-xs text-orange-700 font-medium mb-1">Boas práticas</p>
                <p className="text-xs text-orange-600">Mensagens curtas e renovadas a cada 30s reduzem a taxa de abandono em fila em até 25%.</p>
              </div>
            </div>
          </div>
        )}

        {/* ── Tab: Glossário de Pronúncia ── */}
        {tab === 'glossario' && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-5 h-5 text-purple-600" />
              <h2 className="text-base font-semibold text-gray-900">Glossário de Pronúncia (TTS)</h2>
            </div>
            <p className="text-sm text-gray-500 mb-5">
              Define como o motor de síntese deve pronunciar siglas, marcas e termos técnicos.
              Termos não mapeados são pronunciados letra por letra pelo TTS.
            </p>
            <div className="overflow-hidden rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-700">Termo no texto</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-700">Pronúncia falada</th>
                    <th className="w-12 px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {vc.pronunciationGlossary.map((row, i) => (
                    <tr key={i} className="border-b border-gray-100 last:border-0 group hover:bg-gray-50">
                      <td className="px-4 py-2">
                        <input
                          type="text" value={row.term}
                          onChange={(e) => {
                            const g = [...vc.pronunciationGlossary];
                            g[i] = { ...g[i], term: e.target.value };
                            setVc({ ...vc, pronunciationGlossary: g });
                          }}
                          className="w-full bg-transparent border border-transparent rounded px-1 py-0.5 font-mono focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white focus:border-gray-200"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="text" value={row.pronunciation}
                          onChange={(e) => {
                            const g = [...vc.pronunciationGlossary];
                            g[i] = { ...g[i], pronunciation: e.target.value };
                            setVc({ ...vc, pronunciationGlossary: g });
                          }}
                          className="w-full bg-transparent border border-transparent rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white focus:border-gray-200"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() => removeGlossaryRow(i)}
                          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-gray-50">
                    <td className="px-4 py-2">
                      <input
                        type="text" value={newGlossaryTerm}
                        onChange={(e) => setNewGlossaryTerm(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addGlossaryRow()}
                        placeholder="Novo termo..."
                        className="w-full bg-transparent border border-dashed border-gray-300 rounded px-2 py-1 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white focus:border-solid"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        type="text" value={newGlossaryPron}
                        onChange={(e) => setNewGlossaryPron(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addGlossaryRow()}
                        placeholder="Pronúncia... (Enter para adicionar)"
                        className="w-full bg-transparent border border-dashed border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:bg-white focus:border-solid"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <button onClick={addGlossaryRow} className="p-1 text-gray-400 hover:text-purple-600 transition">
                        <Plus className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Generic Channel Editor ───────────────────────────────────────────────────

interface ChannelEditorProps {
  channel: ChannelConfig;
  onSave: (updated: ChannelConfig) => void;
  onBack: () => void;
}

function ChannelEditor({ channel, onSave, onBack }: ChannelEditorProps) {
  const [local, setLocal] = useState<ChannelConfig>({ ...channel });
  const [newGuideline, setNewGuideline] = useState('');
  const Icon = getChannelIcon(channel.id);

  const updateGuideline = (idx: number, value: string) => {
    const updated = [...local.guidelines];
    updated[idx] = value;
    setLocal({ ...local, guidelines: updated });
  };

  const removeGuideline = (idx: number) =>
    setLocal({ ...local, guidelines: local.guidelines.filter((_, i) => i !== idx) });

  const addGuideline = () => {
    if (!newGuideline.trim()) return;
    setLocal({ ...local, guidelines: [...local.guidelines, newGuideline.trim()] });
    setNewGuideline('');
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Voltar ao Design Studio
        </button>

        <div className="flex items-center gap-4 mb-6">
          <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', local.iconColor)}>
            <Icon className={cn('w-6 h-6', local.color)} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Tom de Voz — {local.name}</h1>
            <p className="text-sm text-gray-500 mt-0.5">Configure como a Clara comunica neste canal</p>
          </div>
          <button
            onClick={() => onSave(local)}
            className="ml-auto flex items-center gap-2 px-5 py-2.5 bg-[#E10019] text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            <Save className="w-4 h-4" />
            Salvar Configurações
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Identidade no Canal</h2>
            <div className="space-y-5">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1.5 block">Saudação</label>
                <input
                  type="text" value={local.greeting}
                  onChange={(e) => setLocal({ ...local, greeting: e.target.value })}
                  placeholder="Ex: Oi, {nome}!"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white transition"
                />
                <p className="text-xs text-gray-400 mt-1">Use {'{nome}'} para o nome do cliente</p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1.5 block">Tamanho máximo de mensagem</label>
                <input
                  type="number" value={local.maxLength}
                  onChange={(e) => setLocal({ ...local, maxLength: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white transition"
                />
                <p className="text-xs text-gray-400 mt-1">Caracteres por mensagem</p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-3 block">
                  Nível de Formalidade —{' '}
                  <span className="font-semibold text-gray-900">{formalityLabel(local.formalityLevel)}</span>
                </label>
                <input
                  type="range" min={0} max={100} value={local.formalityLevel}
                  onChange={(e) => setLocal({ ...local, formalityLevel: Number(e.target.value) })}
                  className="w-full accent-[#E10019]"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>Informal</span>
                  <span>Formal</span>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                <div>
                  <div className="text-sm font-medium text-gray-900">Permitir emojis</div>
                  <div className="text-xs text-gray-500">Habilita uso de emojis nas mensagens</div>
                </div>
                <Toggle on={local.useEmoji} onToggle={() => setLocal({ ...local, useEmoji: !local.useEmoji })} />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Preview da Mensagem</h2>
            <div className={cn('rounded-lg p-4 mb-4', local.bgColor)}>
              <textarea
                value={local.sampleMessage}
                onChange={(e) => setLocal({ ...local, sampleMessage: e.target.value })}
                rows={4}
                className="w-full text-sm text-gray-700 bg-transparent border-0 resize-none focus:outline-none focus:ring-0 leading-relaxed"
                placeholder="Escreva um exemplo de mensagem para este canal..."
              />
            </div>
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>{local.sampleMessage.length} / {local.maxLength} caracteres</span>
              <span className={cn('px-2 py-0.5 rounded-full font-medium', local.useEmoji ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500')}>
                {local.useEmoji ? 'Emojis: ON' : 'Emojis: OFF'}
              </span>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Formalidade</div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className="bg-[#E10019] h-2 rounded-full transition-all" style={{ width: `${local.formalityLevel}%` }} />
              </div>
              <div className="text-xs text-gray-500 mt-1">{formalityLabel(local.formalityLevel)}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
            <h2 className="text-base font-semibold text-gray-900 mb-4">Diretrizes do Canal</h2>
            <div className="space-y-2 mb-4">
              {local.guidelines.map((g, idx) => (
                <div key={idx} className="flex items-center gap-3 group">
                  <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0" />
                  <input
                    type="text" value={g}
                    onChange={(e) => updateGuideline(idx, e.target.value)}
                    className="flex-1 px-3 py-1.5 text-sm border border-transparent rounded-lg bg-gray-50 hover:border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white transition"
                  />
                  <button onClick={() => removeGuideline(idx)} className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <Plus className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <input
                type="text" value={newGuideline}
                onChange={(e) => setNewGuideline(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addGuideline()}
                placeholder="Adicionar diretriz... (Enter para confirmar)"
                className="flex-1 px-3 py-1.5 text-sm border border-dashed border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white focus:border-solid transition"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

/**
 * Conversation Design Studio.
 *
 * A configuração vem da API e volta para ela: salvar aqui muda o tom de voz da
 * Claro em todos os canais integrados já na próxima mensagem, sem deploy.
 */
export default function DesignStudio() {
  const state = useStudioConfig();
  return (
    <AsyncBoundary state={state} loadingLabel="Carregando a configuração da persona…">
      {(config) => <DesignStudioView config={config} reload={state.reload} />}
    </AsyncBoundary>
  );
}

function DesignStudioView({ config, reload }: { config: StudioConfig; reload: () => void }) {
  const [activeChannel, setActiveChannel] = useState<ChannelConfig | null>(null);
  const [channels, setChannels] = useState<ChannelConfig[]>(
    () => toUiChannels(config) as ChannelConfig[]);
  const [intents, setIntents] = useState(config.intents);
  const [guardrails] = useState(config.guardrails);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [personaName, setPersonaName] = useState(config.persona.name);
  const [personaDescription, setPersonaDescription] = useState(config.persona.description);
  const [traits] = useState(config.persona.traits);
  const [saved, setSaved] = useState(false);

  // Mantém a tela em sincronia quando a configuração do servidor muda.
  useEffect(() => {
    setChannels(toUiChannels(config) as ChannelConfig[]);
    setIntents(config.intents);
    setPersonaName(config.persona.name);
    setPersonaDescription(config.persona.description);
  }, [config]);

  const handleSave = async (updated: ChannelConfig) => {
    setSaveError(null);
    // Atualização otimista: a tela responde na hora e o servidor confirma depois.
    setChannels(channels.map((c) => (c.id === updated.id ? updated : c)));
    setActiveChannel(null);
    try {
      await api.saveChannelConfig(updated.id, toApiPatch(updated as never));
      reload();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Falha ao salvar o canal');
      reload();  // desfaz a otimista voltando ao estado do servidor
    }
  };

  if (activeChannel) {
    return activeChannel.id === 'voice'
      ? <VoiceChannelEditor channel={activeChannel} onBack={() => setActiveChannel(null)} onSave={handleSave} />
      : <ChannelEditor channel={activeChannel} onBack={() => setActiveChannel(null)} onSave={handleSave} />;
  }

  const handleSaveAll = async () => {
    setSaveError(null);
    try {
      await api.saveStudioConfig({
        ...config,
        persona: { ...config.persona, name: personaName, description: personaDescription },
        intents,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      reload();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Falha ao salvar');
    }
  };


  return (
    <div className="h-full overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Conversation Design Studio</h1>
            <p className="text-sm text-gray-600 mt-1">
              Configure a personalidade, tom de voz e regras que definem como a Clara interage com clientes
            </p>
          </div>
          {saveError && (
            <span className="text-sm text-[#E10019] mr-3">{saveError}</span>
          )}
          <button
            onClick={handleSaveAll}
            className={cn('flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-all', saved ? 'bg-green-600 text-white' : 'bg-[#E10019] text-white hover:bg-red-700')}
          >
            <Save className="w-4 h-4" />
            {saved ? 'Salvo!' : 'Salvar Alterações'}
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Persona */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
                <User className="w-5 h-5 text-[#E10019]" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Persona da Marca</h2>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1.5 block">Nome</label>
                <input
                  type="text" value={personaName}
                  onChange={(e) => setPersonaName(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white transition"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1.5 block">Descrição</label>
                <textarea
                  rows={4} value={personaDescription}
                  onChange={(e) => setPersonaDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white transition resize-none"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">Características</label>
                <div className="flex flex-wrap gap-2">
                  {traits.map((trait) => (
                    <span key={trait} className="px-3 py-1 bg-red-50 text-[#E10019] rounded-full text-sm font-medium border border-red-100">
                      {trait}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Intents */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-purple-50 flex items-center justify-center">
                <Code2 className="w-5 h-5 text-purple-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Intents Principais</h2>
            </div>
            <div className="space-y-2">
              {intents.map((intent, idx) => (
                <div key={idx} className="flex items-center gap-3 group p-2 rounded-lg hover:bg-gray-50">
                  <input
                    type="text" value={intent.name}
                    onChange={(e) => {
                      const updated = [...intents];
                      updated[idx] = { ...updated[idx], name: e.target.value };
                      setIntents(updated);
                    }}
                    className="flex-1 text-sm font-medium text-gray-900 bg-transparent border border-transparent rounded px-1 focus:outline-none focus:ring-2 focus:ring-[#E10019] focus:bg-white focus:border-gray-200"
                  />
                  <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0', intent.confidence === 'Alta' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700')}>
                    {intent.confidence}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Channel Cards */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center">
                <Globe className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Configuração por Canal</h2>
                <p className="text-sm text-gray-500">Clique em um canal para editar sua configuração específica</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {channels.map((ch) => {
                const Icon = getChannelIcon(ch.id);
                const isVoice = ch.id === 'voice';
                const vc = ch.voiceConfig;
                return (
                  <button
                    key={ch.id}
                    onClick={() => setActiveChannel(ch)}
                    className="text-left p-4 border border-gray-200 rounded-xl hover:border-[#E10019] hover:shadow-sm group transition-all"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', ch.bgColor)}>
                        <Icon className={cn('w-5 h-5', ch.color)} />
                      </div>
                      <Edit3 className="w-4 h-4 text-gray-300 group-hover:text-[#E10019] transition-colors" />
                    </div>
                    <div className="font-semibold text-sm text-gray-900 mb-1">{ch.name}</div>
                    {isVoice && vc ? (
                      <>
                        <div className="text-xs text-gray-500 mb-2">
                          {vc.voiceGender === 'feminino' ? 'Feminino' : 'Masculino'} · {speechRateLabel(vc.speechRate)}
                        </div>
                        <div className={cn('text-xs px-2 py-0.5 rounded-full inline-block', ch.bgColor, ch.color)}>
                          {vc.captureMode === 'dtmf' ? 'DTMF' : vc.captureMode === 'voice' ? 'Voz' : 'Híbrido'}
                        </div>
                        <p className="text-xs text-gray-400 mt-3 line-clamp-2 leading-relaxed">
                          "{vc.scriptOpening}"
                        </p>
                      </>
                    ) : (
                      <>
                        <div className="text-xs text-gray-500 mb-2">{formalityLabel(ch.formalityLevel)}</div>
                        <div className={cn('text-xs px-2 py-0.5 rounded-full inline-block', ch.bgColor, ch.color)}>
                          {ch.useEmoji ? 'Emojis ON' : 'Emojis OFF'}
                        </div>
                        <p className="text-xs text-gray-400 mt-3 line-clamp-2 leading-relaxed">
                          "{ch.sampleMessage}"
                        </p>
                      </>
                    )}
                    <div className="flex items-center gap-1 mt-3 text-xs font-medium text-[#E10019] opacity-0 group-hover:opacity-100 transition-opacity">
                      Editar configuração
                      <ChevronRight className="w-3.5 h-3.5" />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Guardrails */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 lg:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-orange-50 flex items-center justify-center">
                <Shield className="w-5 h-5 text-orange-600" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900">Guardrails</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {guardrails.map((guardrail, idx) => (
                <div key={idx} className="p-4 bg-gray-50 rounded-lg border border-gray-200 flex items-start justify-between">
                  <p className="text-sm text-gray-800 flex-1 pr-3">{guardrail.rule}</p>
                  <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full flex-shrink-0 font-medium">
                    {guardrail.category}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Efeito da configuração dentro da conversa */}
          <PersonaImpact version={config.version} />
        </div>
      </div>
    </div>
  );
}
