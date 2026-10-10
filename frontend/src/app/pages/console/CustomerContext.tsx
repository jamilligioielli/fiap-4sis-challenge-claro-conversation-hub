import { useState } from 'react';
import { Link, useParams } from 'react-router';
import {
  ArrowLeft, MessageCircle, Smartphone, User, CreditCard, TrendingUp, Heart,
  Mail, Phone, Globe,
} from 'lucide-react';

import { useCustomerContext, useCustomerConversationHistory } from '../../api/hooks';
import type {
  ConversationHistoryItem, CustomerContext as CustomerContextData,
} from '../../api/types';
import { AsyncBoundary, EmptyState } from '../../components/AsyncBoundary';
import CustomerSnapshot from '../../components/context/CustomerSnapshot';
import ConversationHistoryModal from '../../components/history/ConversationHistoryModal';
import ConversationTimeline from '../../components/history/ConversationTimeline';
import ConversationTimelineInsights from '../../components/history/ConversationTimelineInsights';
import { cn } from '../../components/ui/utils';

/**
 * Visão 360° do cliente.
 *
 * É o contexto que sustenta a promessa da solução: por existir num só lugar,
 * indexado pelo cliente e não pelo canal, ninguém precisa se reapresentar ao
 * trocar de ponto de contato. Toda consulta a esta tela entra na trilha de
 * auditoria da LGPD, no back-end.
 */

const timelineIcons: Record<string, typeof MessageCircle> = {
  conversation: MessageCircle, channel: TrendingUp, app: Smartphone,
  support: User, payment: CreditCard, plan: TrendingUp,
};

const timelineColors: Record<string, string> = {
  conversation: 'bg-blue-100 text-blue-600',
  channel: 'bg-green-100 text-green-600',
  app: 'bg-purple-100 text-purple-600',
  support: 'bg-orange-100 text-orange-600',
  payment: 'bg-green-100 text-green-600',
  plan: 'bg-red-100 text-red-600',
};

const brl = (value: number) =>
  value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export default function CustomerContextPage() {
  const { id } = useParams<{ id: string }>();
  const state = useCustomerContext(id);

  // Cliente ainda não identificado não é erro: é um estado legítimo do produto.
  // Quem escreve pela primeira vez num canal aberto não tem cadastro no hub, e a
  // tela precisa dizer isso — e não devolver uma mensagem de falha.
  if (state.error?.includes('não encontrado')) {
    return (
      <div className="p-6">
        <Link to="/console/inbox"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-6">
          <ArrowLeft className="w-4 h-4" />
          Voltar para o Inbox
        </Link>
        <EmptyState
          title="Cliente ainda não identificado"
          description={'Esta conversa começou num canal aberto e o cliente ainda não foi '
            + 'vinculado a um cadastro. Assim que ele se identificar, o histórico entre '
            + 'canais passa a alimentar esta tela automaticamente.'}
          icon={<User className="w-12 h-12" />}
        />
      </div>
    );
  }

  return (
    <AsyncBoundary state={state} loadingLabel="Carregando o contexto do cliente…">
      {(customer) => <ContextView customer={customer} />}
    </AsyncBoundary>
  );
}

function ContextView({ customer }: { customer: CustomerContextData }) {
  const history = useCustomerConversationHistory(customer.id);
  const [opened, setOpened] = useState<ConversationHistoryItem | null>(null);

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      <div className="mb-6">
        <Link to="/console/inbox"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-3">
          <ArrowLeft className="w-4 h-4" />
          Voltar para o Inbox
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Contexto do Cliente</h1>
        <p className="text-sm text-gray-600">
          Visão 360° que alimenta a IA e os atendentes em tempo real
        </p>
      </div>

      {/* Resumo em três cartões: quem é, o que tratou por último, como costuma ser. */}
      <div className="mb-6">
        <CustomerSnapshot
          layout="row"
          customer={customer}
          history={history.data}
          onOpenHistory={() => document.getElementById('historico-conversas')
            ?.scrollIntoView({ behavior: 'smooth' })}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* -------------------------------------------------- coluna 1 */}
        <div className="space-y-6">
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Perfil do Cliente</h3>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-14 h-14 rounded-full bg-[#E10019] flex items-center justify-center text-white font-semibold text-lg">
                {customer.name.split(' ').slice(0, 2).map((p) => p[0]).join('')}
              </div>
              <div>
                <p className="font-medium text-gray-900">{customer.name}</p>
                <span className="inline-flex items-center gap-1 mt-1 px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                  <Heart className="w-3 h-3" />
                  {customer.segment}
                </span>
              </div>
            </div>
            <dl className="space-y-2 text-sm">
              <Row label="CPF" value={customer.document_masked || '—'} />
              <Row label="Nascimento" value={customer.birth_date || '—'} />
              <Row label="Cliente desde" value={customer.customer_since || '—'} />
              <Row label="Conversas" value={String(customer.conversation_count)} />
            </dl>
          </section>

          {customer.plan && (
            <section className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-4">Plano Contratado</h3>
              <div className="p-4 rounded-lg bg-gradient-to-br from-[#E10019] to-orange-500 text-white mb-4">
                <p className="font-semibold text-lg">{customer.plan.name}</p>
                <p className="text-2xl font-bold mt-1">
                  {brl(customer.plan.price)}<span className="text-sm font-normal">/mês</span>
                </p>
                {customer.plan.line && (
                  <p className="text-sm text-white/80 mt-1">{customer.plan.line}</p>
                )}
              </div>
              <div className="mb-3">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Franquia</span>
                  <span className="text-gray-900 font-medium">
                    {customer.plan.used_gb}GB / {customer.plan.data_gb}GB
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn('h-2 rounded-full',
                      customer.plan.usage_percent >= 85 ? 'bg-orange-500' : 'bg-[#E10019]')}
                    style={{ width: `${Math.min(customer.plan.usage_percent, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {customer.plan.usage_percent}% utilizado
                </p>
              </div>
              <dl className="space-y-2 text-sm">
                <Row label="Vencimento" value={`Todo dia ${customer.plan.due_day}`} />
                <Row label="Status" value={customer.plan.status} />
              </dl>
            </section>
          )}

          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Preferências de Contato</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                <MessageCircle className="w-4 h-4 text-green-600" />
                <span className="text-gray-700">Canal preferido:</span>
                <span className="font-medium text-gray-900 capitalize">
                  {customer.preferred_channel}
                </span>
              </div>
              {customer.email && (
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-700">{customer.email}</span>
                </div>
              )}
              {customer.phone && (
                <div className="flex items-center gap-2">
                  <Phone className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-700">{customer.phone}</span>
                </div>
              )}
              {customer.channels_used.length > 0 && (
                <div className="flex items-start gap-2 pt-2 border-t border-gray-100">
                  <Globe className="w-4 h-4 text-gray-400 mt-0.5" />
                  <div>
                    <p className="text-gray-500 text-xs">Canais já utilizados</p>
                    <p className="text-gray-900 font-medium capitalize">
                      {customer.channels_used.join(' · ')}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* -------------------------------------------------- coluna 2 */}
        <div className="space-y-6">
          {customer.products.length > 0 && (
            <section className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-4">Produtos Ativos</h3>
              <div className="space-y-3">
                {customer.products.map((product) => (
                  <div key={product.name} className="p-3 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-gray-900 text-sm">{product.name}</p>
                      <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">
                        {product.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">{product.description}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {customer.upgrade_options.length > 0 && (
            <section className="rounded-xl border border-green-200 bg-gradient-to-br from-green-50 to-emerald-50 p-5">
              <h3 className="font-semibold text-gray-900 mb-2">Elegibilidade para Upgrade</h3>
              <p className="text-xs text-gray-600 mb-4">
                Calculado a partir do consumo da franquia e do histórico de pagamento.
              </p>
              <div className="space-y-2">
                {customer.upgrade_options.map((option) => (
                  <div key={option.name}
                    className="flex items-center justify-between p-2.5 bg-white/70 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{option.name}</p>
                      <p className="text-xs text-gray-500">{brl(option.price)}/mês</p>
                    </div>
                    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium',
                      option.status === 'Recomendado'
                        ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-600')}>
                      {option.status}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Risco de Churn</h3>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600">Probabilidade</span>
              <span className="font-medium text-gray-900">
                {Math.round(customer.churn_risk * 100)}% ({customer.churn_label})
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
              <div
                className={cn('h-2 rounded-full',
                  customer.churn_risk < 0.25 ? 'bg-green-500'
                    : customer.churn_risk < 0.6 ? 'bg-amber-500' : 'bg-[#E10019]')}
                style={{ width: `${Math.max(customer.churn_risk * 100, 3)}%` }}
              />
            </div>
            <ul className="space-y-2 text-sm">
              {customer.churn_factors.map((factor) => (
                <li key={factor.text} className="flex items-center gap-2">
                  <span className={cn('w-1.5 h-1.5 rounded-full shrink-0',
                    factor.positive ? 'bg-green-500' : 'bg-orange-500')} />
                  <span className="text-gray-700">{factor.text}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* -------------------------------------------------- coluna 3 */}
        <div className="space-y-6">
          <section id="historico-conversas" className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Histórico de Conversas</h3>
            {history.loading && !history.data && (
              <p className="text-sm text-gray-500">Carregando o histórico…</p>
            )}
            {history.error && !history.data && (
              <p className="text-sm text-gray-500">Histórico indisponível agora.</p>
            )}
            {history.data && (
              <>
                <ConversationTimeline items={history.data.items} onSelect={setOpened} />
                <ConversationTimelineInsights insights={history.data.insights}
                                              months={history.data.months} />
              </>
            )}
          </section>

          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">Eventos da Conta</h3>
            {customer.timeline.length === 0 ? (
              <p className="text-sm text-gray-500">Nenhum evento registrado ainda.</p>
            ) : (
              <div className="space-y-4">
                {customer.timeline.map((event, index) => {
                  const Icon = timelineIcons[event.type] ?? MessageCircle;
                  const color = timelineColors[event.type] ?? 'bg-gray-100 text-gray-600';
                  return (
                    <div key={`${event.date}-${index}`} className="flex gap-3">
                      <div className={cn('w-8 h-8 rounded-full flex items-center justify-center shrink-0',
                                          color)}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0 pb-1">
                        <p className="text-sm text-gray-900">{event.event}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{event.date}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Como este contexto é usado</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              {[
                'Alimenta as sugestões da IA em tempo real',
                'Garante continuidade entre canais sem repetição de dados',
                'Identifica oportunidades de upsell e cross-sell',
                'Detecta insatisfação e risco de churn',
              ].map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-3 pt-3 border-t border-blue-200 text-xs text-gray-600">
              Cada abertura desta tela é registrada na trilha de auditoria de acesso (LGPD).
            </p>
          </section>
        </div>
      </div>

      <ConversationHistoryModal item={opened} onClose={() => setOpened(null)} />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-gray-900 font-medium">{value}</dd>
    </div>
  );
}
