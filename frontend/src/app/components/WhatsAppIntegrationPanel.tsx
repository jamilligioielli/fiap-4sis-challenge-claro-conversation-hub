import { useState } from 'react';
import {
  CheckCircle2, Copy, Check, MessageCircle, ShieldCheck, ShieldAlert,
  XCircle, Send, Loader2, ChevronDown, ChevronRight,
} from 'lucide-react';

import { api } from '../api/client';
import { useWhatsAppStatus } from '../api/hooks';
import { cn } from './ui/utils';

/**
 * Estado da integração com a WhatsApp Business Cloud API.
 *
 * Mostra o que está configurado, o que falta e a URL exata do webhook para
 * colar no painel da Meta. O envio de teste existe para validar credenciais
 * antes da gravação — token da Meta expira em 24h no modo de desenvolvimento,
 * e descobrir isso durante a demonstração é tarde demais.
 *
 * Nenhum token aparece aqui: a API devolve apenas `configurado` ou `ausente`.
 */
export default function WhatsAppIntegrationPanel() {
  const status = useWhatsAppStatus();
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [testText, setTestText] = useState('Teste de integração do Claro Conversation Hub.');
  const [testTo, setTestTo] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  const s = status.data;

  async function copyWebhook() {
    if (!s) return;
    try {
      await navigator.clipboard.writeText(s.webhook_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setResult({ ok: false, message: 'O navegador bloqueou a cópia. Selecione a URL à mão.' });
    }
  }

  async function sendTest() {
    setSending(true);
    setResult(null);
    try {
      await api.sendWhatsAppTest(testText, testTo || undefined);
      setResult({ ok: true, message: 'Mensagem enviada. Confira o aparelho do destinatário.' });
    } catch (err) {
      setResult({ ok: false, message: err instanceof Error ? err.message : 'Falha no envio' });
    } finally {
      setSending(false);
    }
  }

  const state = !s ? 'loading'
    : s.can_send ? 'live'
    : s.configured ? 'configured'
    : 'inactive';

  const badge = {
    loading: { label: 'verificando…', className: 'bg-gray-100 text-gray-500' },
    live: { label: 'ativo', className: 'bg-green-100 text-green-700' },
    configured: { label: 'configurado · desligado', className: 'bg-amber-100 text-amber-700' },
    inactive: { label: 'simulador apenas', className: 'bg-gray-100 text-gray-600' },
  }[state];

  return (
    <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 p-4 hover:bg-gray-50 transition-colors text-left"
      >
        <MessageCircle className="w-4 h-4 text-green-600 shrink-0" />
        <h4 className="font-semibold text-gray-900 text-sm">WhatsApp Business API</h4>
        <span className={cn('ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium',
                            badge.className)}>
          {badge.label}
        </span>
        {open ? <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
              : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
          {status.error && (
            <p className="text-xs text-[#E10019]">{status.error}</p>
          )}

          {s && (
            <>
              {/* checklist de configuração */}
              <div className="space-y-1.5">
                {[
                  ['Número (phone_number_id)', !!s.phone_number_id],
                  ['Token de acesso', s.access_token === 'configurado'],
                  ['Token de verificação', s.verify_token === 'configurado'],
                  ['Validação de assinatura', s.signature_validation],
                  ['Canal ligado (WHATSAPP_ENABLED)', s.enabled],
                ].map(([label, ok]) => (
                  <div key={label as string} className="flex items-center gap-2 text-xs">
                    {ok
                      ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
                      : <XCircle className="w-3.5 h-3.5 text-gray-300 shrink-0" />}
                    <span className={ok ? 'text-gray-700' : 'text-gray-400'}>{label}</span>
                  </div>
                ))}
              </div>

              {s.missing.length > 0 && (
                <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-900 font-medium mb-1">
                    Faltam no <code>.env</code>:
                  </p>
                  <ul className="text-[11px] text-amber-800 font-mono space-y-0.5">
                    {s.missing.map((v) => <li key={v}>{v}</li>)}
                  </ul>
                </div>
              )}

              {!s.signature_validation && s.configured && (
                <div className="flex items-start gap-2 p-2.5 bg-red-50 border border-red-200 rounded-lg">
                  <ShieldAlert className="w-3.5 h-3.5 text-[#E10019] shrink-0 mt-0.5" />
                  <p className="text-[11px] text-red-900">
                    Sem <code>WHATSAPP_APP_SECRET</code> o webhook aceita qualquer payload.
                    Aceitável em desenvolvimento; nunca em produção.
                  </p>
                </div>
              )}

              {s.signature_validation && (
                <div className="flex items-center gap-2 text-xs text-green-700">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Assinatura do webhook validada (HMAC SHA-256)
                </div>
              )}

              {/* webhook */}
              <div>
                <p className="text-xs text-gray-400 mb-1">
                  URL do webhook — cole no painel da Meta
                </p>
                <div className="flex items-center gap-1.5">
                  <code className="flex-1 px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-[10px] text-gray-700 break-all">
                    {s.webhook_url}
                  </code>
                  <button
                    onClick={copyWebhook}
                    className="p-1.5 hover:bg-gray-100 rounded transition-colors shrink-0"
                    title="Copiar"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-green-600" />
                            : <Copy className="w-3.5 h-3.5 text-gray-500" />}
                  </button>
                </div>
                <p className="text-[10px] text-gray-400 mt-1">
                  Campo a assinar: <code>messages</code>. Em desenvolvimento, exponha a API
                  com <code>ngrok http 8000</code> e ajuste <code>PUBLIC_URL</code>.
                </p>
              </div>

              {/* envio de teste */}
              {s.can_send && (
                <div className="pt-3 border-t border-gray-100">
                  <p className="text-xs text-gray-400 mb-2">Enviar mensagem de teste</p>
                  <input
                    value={testTo}
                    onChange={(e) => setTestTo(e.target.value)}
                    placeholder={s.default_recipient
                      ? `padrão: ${s.default_recipient}` : '5511987654321'}
                    className="w-full mb-1.5 px-2.5 py-1.5 bg-gray-50 border border-gray-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-green-600"
                  />
                  <textarea
                    value={testText}
                    onChange={(e) => setTestText(e.target.value)}
                    rows={2}
                    className="w-full mb-2 px-2.5 py-1.5 bg-gray-50 border border-gray-200 rounded text-xs resize-none focus:outline-none focus:ring-1 focus:ring-green-600"
                  />
                  <button
                    onClick={sendTest}
                    disabled={sending || !testText.trim()}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 transition-colors disabled:opacity-40"
                  >
                    {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                             : <Send className="w-3.5 h-3.5" />}
                    Enviar pelo WhatsApp real
                  </button>
                  <p className="text-[10px] text-gray-400 mt-1.5">
                    O destinatário precisa estar na lista de números de teste do app na Meta.
                  </p>
                </div>
              )}

              {result && (
                <p className={cn('text-xs', result.ok ? 'text-green-700' : 'text-[#E10019]')}>
                  {result.message}
                </p>
              )}

              {!s.configured && (
                <p className="text-[11px] text-gray-500 pt-1">
                  Sem credenciais, o canal WhatsApp funciona apenas pelo simulador acima — o
                  que é suficiente para demonstrar todos os requisitos funcionais. As
                  instruções de configuração estão em <code>.env.example</code>.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
