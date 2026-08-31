import { useState } from 'react';
import { Link } from 'react-router';
import {
  Megaphone, ShieldCheck, ShieldAlert, Clock, TrendingUp, Send, Loader2,
  CheckCircle2, FileText, Ban, ExternalLink, Info,
} from 'lucide-react';

import { api } from '../../api/client';
import { useEligibleCustomers } from '../../api/hooks';
import type { EligibleCustomer, OutreachResult } from '../../api/types';
import { AsyncBoundary, EmptyState } from '../../components/AsyncBoundary';
import { cn } from '../../components/ui/utils';

/**
 * Contato ativo — quando é a Claro que começa a conversa.
 *
 * Atender bem quem procura é metade do problema; a outra metade é procurar a
 * pessoa certa na hora certa, sem virar incômodo. Por isso a tela mostra o
 * motivo de cada indicação e, com o mesmo destaque, o que impede o contato:
 * consentimento ausente e a janela de 24 horas do WhatsApp não são detalhes de
 * implementação, são o que separa uma abordagem legítima de spam.
 */
export default function Outreach() {
  const state = useEligibleCustomers();
  const [sending, setSending] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, OutreachResult>>({});
  const [error, setError] = useState<string | null>(null);

  async function send(customer: EligibleCustomer) {
    if (!customer.suggested_offer || sending) return;
    setSending(customer.customer_id);
    setError(null);
    try {
      const result = await api.sendOutreach(customer.customer_id, customer.suggested_offer.id);
      setResults((prev) => ({ ...prev, [customer.customer_id]: result }));
      state.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao enviar a abordagem');
    } finally {
      setSending(null);
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-1">
          Quem vale a pena procurar hoje
        </h2>
        <p className="text-sm text-gray-600 max-w-3xl">
          O hub cruza consumo, plano, tempo de casa e risco de saída para sugerir quem tem
          algo a ganhar com uma oferta — e verifica, antes de qualquer envio, se a Claro
          tem permissão para falar.
        </p>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-[#E10019]">
          {error}
        </div>
      )}

      <AsyncBoundary
        state={state}
        loadingLabel="Avaliando a base…"
        empty={<EmptyState title="Ninguém elegível no momento" />}
      >
        {(customers) => (
          customers.length === 0 ? (
            <EmptyState
              title="Ninguém elegível no momento"
              description="A elegibilidade é calculada sobre o perfil e o consumo dos clientes cadastrados."
              icon={<Megaphone className="w-12 h-12" />}
            />
          ) : (
            <div className="space-y-4">
              {customers.map((customer) => (
                <EligibleCard
                  key={customer.customer_id}
                  customer={customer}
                  sending={sending === customer.customer_id}
                  result={results[customer.customer_id]}
                  onSend={() => send(customer)}
                />
              ))}
            </div>
          )
        )}
      </AsyncBoundary>

      <div className="mt-8 p-4 bg-gray-50 border border-gray-200 rounded-xl flex items-start gap-3">
        <Info className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
        <p className="text-xs text-gray-600 leading-relaxed">
          As duas regras verificadas aqui vêm da política oficial da API do WhatsApp Business:
          o contato exige consentimento explícito para receber ofertas, e fora da janela de
          24 horas desde a última mensagem do cliente a mensagem só pode sair por modelo
          previamente aprovado pela Meta. O hub não contorna nenhuma das duas — quando não
          pode enviar livremente, ele diz por quê.
        </p>
      </div>
    </div>
  );
}

function EligibleCard({ customer, sending, result, onSend }: {
  customer: EligibleCustomer;
  sending: boolean;
  result?: OutreachResult;
  onSend: () => void;
}) {
  const offer = customer.suggested_offer;
  const initials = customer.customer_name.split(' ').slice(0, 2).map((p) => p[0]).join('');

  return (
    <article className={cn(
      'bg-white rounded-xl border p-5',
      customer.can_contact ? 'border-gray-200' : 'border-gray-200 bg-gray-50/60',
    )}>
      <div className="flex items-start gap-4">
        <div className={cn(
          'w-11 h-11 rounded-full flex items-center justify-center text-white text-sm font-semibold shrink-0',
          customer.can_contact ? 'bg-[#E10019]' : 'bg-gray-400',
        )}>
          {initials}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h3 className="font-semibold text-gray-900">{customer.customer_name}</h3>
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
              {customer.segment}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-violet-50 text-violet-700 rounded-full text-xs font-medium">
              <TrendingUp className="w-3 h-3" />
              afinidade {customer.score.toFixed(2)}
            </span>
          </div>

          {/* por que este cliente */}
          <div className="flex flex-wrap gap-1.5 mt-2 mb-3">
            {customer.reasons.map((reason) => (
              <span
                key={reason.code}
                className="px-2 py-1 bg-emerald-50 text-emerald-800 rounded text-xs"
                title={`peso ${reason.weight}`}
              >
                {reason.description}
              </span>
            ))}
          </div>

          {/* permissões */}
          <div className="flex flex-wrap items-center gap-3 text-xs mb-3">
            <span className={cn('inline-flex items-center gap-1.5 font-medium',
              customer.marketing_opt_in ? 'text-emerald-700' : 'text-[#E10019]')}>
              {customer.marketing_opt_in
                ? <><ShieldCheck className="w-3.5 h-3.5" /> aceita receber ofertas</>
                : <><ShieldAlert className="w-3.5 h-3.5" /> sem consentimento para oferta</>}
            </span>
            <span className={cn('inline-flex items-center gap-1.5',
              customer.window_open ? 'text-gray-700' : 'text-amber-700 font-medium')}>
              <Clock className="w-3.5 h-3.5" />
              {customer.window_open
                ? `janela de 24h aberta · ${customer.window_hours_remaining.toFixed(0)}h restantes`
                : 'janela de 24h fechada'}
            </span>
            {customer.requires_template && (
              <span className="inline-flex items-center gap-1.5 text-amber-700">
                <FileText className="w-3.5 h-3.5" />
                exige modelo aprovado
              </span>
            )}
          </div>

          {/* impedimentos */}
          {customer.blocks.length > 0 && (
            <div className="mb-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-xs font-medium text-[#E10019] mb-1 flex items-center gap-1.5">
                <Ban className="w-3.5 h-3.5" />
                Contato bloqueado
              </p>
              <ul className="space-y-0.5">
                {customer.blocks.map((block) => (
                  <li key={block.code} className="text-xs text-red-900">• {block.description}</li>
                ))}
              </ul>
            </div>
          )}

          {/* oferta sugerida */}
          {offer && (
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-sm font-medium text-gray-900">{offer.title}</span>
                {offer.price != null && (
                  <span className="text-sm text-[#E10019] font-semibold">
                    R$ {offer.price.toFixed(2).replace('.', ',')}/mês
                  </span>
                )}
                <span className="px-1.5 py-0.5 bg-white border border-gray-200 text-gray-500 rounded text-[10px] font-mono">
                  {offer.category}
                </span>
              </div>
              <p className="text-xs text-gray-600">{offer.pitch}</p>
              {offer.saving_hint && (
                <p className="text-xs text-emerald-700 mt-1">{offer.saving_hint}</p>
              )}
            </div>
          )}
        </div>

        <div className="shrink-0 w-44 flex flex-col items-stretch gap-2">
          {result ? (
            <div className="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-center">
              <p className="text-xs font-medium text-emerald-800 flex items-center justify-center gap-1.5 mb-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                abordagem enviada
              </p>
              <p className="text-[11px] text-emerald-700">
                {result.used_template ? 'por modelo aprovado' : 'mensagem livre'}
                {' · '}{result.template_category}
              </p>
              <Link
                to={`/console/conversation/${result.conversation_id}`}
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-[#E10019] font-medium hover:underline"
              >
                ver a conversa <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          ) : (
            <button
              onClick={onSend}
              disabled={!customer.can_contact || !offer || sending}
              className={cn(
                'flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                customer.can_contact && offer
                  ? 'bg-[#E10019] text-white hover:bg-[#C20015]'
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed',
              )}
            >
              {sending
                ? <><Loader2 className="w-4 h-4 animate-spin" /> enviando…</>
                : <><Send className="w-4 h-4" /> Abordar cliente</>}
            </button>
          )}

          {!result && !customer.can_contact && (
            <p className="text-[11px] text-gray-500 text-center leading-relaxed">
              O hub recusa o envio enquanto o impedimento existir.
            </p>
          )}

          <Link
            to={`/console/customer-context/${customer.customer_id}`}
            className="text-center text-xs text-gray-500 hover:text-gray-900 hover:underline"
          >
            ver contexto do cliente
          </Link>
        </div>
      </div>
    </article>
  );
}
