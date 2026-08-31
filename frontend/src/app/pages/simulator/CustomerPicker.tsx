import { Link } from 'react-router';
import {
  ArrowLeft, MessageCircle, Globe, Smartphone, Phone, ChevronRight,
  Heart, AlertTriangle, MessageSquare, BellOff, BellRing,
} from 'lucide-react';

import { useCustomers } from '../../api/hooks';
import type { Channel, CustomerSummary } from '../../api/types';
import { AsyncBoundary } from '../../components/AsyncBoundary';
import { cn } from '../../components/ui/utils';

/**
 * Escolha da persona.
 *
 * Simular sem escolher quem se é produz um "cliente não identificado" — e um
 * cliente não identificado não tem plano, histórico nem perfil, que é
 * justamente o contexto que a solução existe para usar. Escolher aqui é o que
 * torna a conversa seguinte diferente de um chat genérico.
 */

const channelIcons: Record<Channel, typeof MessageCircle> = {
  whatsapp: MessageCircle, web: Globe, app: Smartphone, voice: Phone,
};

const channelLabels: Record<Channel, string> = {
  whatsapp: 'WhatsApp', web: 'Web Chat', app: 'App Claro', voice: 'Voz',
};

export default function CustomerPicker() {
  const state = useCustomers();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <Link to="/"
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-3">
            <ArrowLeft className="w-4 h-4" />
            Trocar de visão
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Com quem você quer conversar?</h1>
          <p className="text-sm text-gray-600 mt-1">
            Cada cliente tem plano, histórico e comportamento próprios — e o assistente
            leva isso em conta na resposta.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <AsyncBoundary state={state} loadingLabel="Carregando clientes…">
          {(customers) => (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {customers.map((customer) => (
                <CustomerCard key={customer.id} customer={customer} />
              ))}
            </div>
          )}
        </AsyncBoundary>
      </main>
    </div>
  );
}

function CustomerCard({ customer }: { customer: CustomerSummary }) {
  const ChannelIcon = channelIcons[customer.preferred_channel];
  const initials = customer.name.split(' ').slice(0, 2).map((p) => p[0]).join('');
  const highUsage = (customer.plan_usage_percent ?? 0) >= 80;
  const atRisk = customer.churn_label === 'Alto';

  return (
    <Link
      to={`/simulador/${customer.id}`}
      className="group block bg-white rounded-xl border border-gray-200 p-5 hover:border-[#E10019] hover:shadow-md transition-all"
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="w-12 h-12 rounded-full bg-[#E10019] flex items-center justify-center text-white font-semibold shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-gray-900">{customer.name}</h3>
            {customer.segment === 'VIP' && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                <Heart className="w-3 h-3" />
                VIP
              </span>
            )}
            {atRisk && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                <AlertTriangle className="w-3 h-3" />
                risco de saída
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 flex items-center gap-1.5 mt-0.5">
            <ChannelIcon className="w-3.5 h-3.5" />
            prefere {channelLabels[customer.preferred_channel]}
          </p>
        </div>
        <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-[#E10019] transition-colors shrink-0" />
      </div>

      <p className="text-sm text-gray-600 mb-4 leading-relaxed">{customer.persona_summary}</p>

      <div className="flex items-center gap-3 flex-wrap text-xs">
        {customer.plan_name && (
          <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded font-medium">
            {customer.plan_name}
          </span>
        )}
        {customer.plan_usage_percent != null && (
          <span className={cn('px-2 py-1 rounded font-medium',
            highUsage ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-600')}>
            {customer.plan_usage_percent}% da franquia
          </span>
        )}
        <span className={cn('inline-flex items-center gap-1 px-2 py-1 rounded font-medium',
          customer.marketing_opt_in ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500')}>
          {customer.marketing_opt_in
            ? <><BellRing className="w-3 h-3" /> aceita ofertas</>
            : <><BellOff className="w-3 h-3" /> sem opt-in</>}
        </span>
        {customer.conversation_count > 0 && (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded font-medium">
            <MessageSquare className="w-3 h-3" />
            {customer.conversation_count} conversa{customer.conversation_count > 1 ? 's' : ''}
          </span>
        )}
      </div>
    </Link>
  );
}
