import { Link } from 'react-router';
import { ChevronRight, Clock, Globe, MessageCircle, Phone, Smartphone, UserCheck } from 'lucide-react';

import type { Channel, ConversationListItem } from '../../api/types';
import { formatWait, secondsSince, urgencyFor } from '../../lib/urgency';
import { sentimentStyle } from '../../lib/sentiment';
import { cn } from '../ui/utils';

const channelIcons: Record<Channel, typeof Globe> = {
  web: Globe, whatsapp: MessageCircle, app: Smartphone, voice: Phone,
};

const priorityLabels: Record<string, { label: string; className: string }> = {
  high: { label: 'Prioridade alta', className: 'bg-red-100 text-red-700' },
  medium: { label: 'Prioridade média', className: 'bg-amber-100 text-amber-700' },
  low: { label: 'Prioridade baixa', className: 'bg-gray-100 text-gray-600' },
};

/**
 * Uma conversa na fila do atendente.
 *
 * O tempo de espera é o primeiro elemento da linha porque é a informação que
 * decide o que atender primeiro; urgência vai em cor, ícone e texto juntos.
 */
export default function ConversationRowWithUrgency({ conversation, now, position, agent }: {
  conversation: ConversationListItem;
  now: number;
  position: number;
  agent: string;
}) {
  const seconds = secondsSince(conversation.handover_requested_at, now)
    ?? conversation.waiting_seconds ?? 0;
  const urgency = urgencyFor(seconds);
  const Icon = channelIcons[conversation.channel] ?? Globe;
  const priority = priorityLabels[conversation.priority];
  const sentiment = sentimentStyle(conversation.sentiment);
  const mine = conversation.assigned_agent === agent;

  return (
    <li>
      <Link
        to={`/console/conversation/${conversation.id}`}
        className="group relative flex items-stretch gap-4 bg-white border border-gray-200 rounded-xl p-4 pl-5 hover:shadow-md hover:border-gray-300 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E10019]"
        aria-label={`${position}º na fila: ${conversation.customer_name}, esperando há ${formatWait(seconds)}, ${urgency.label}`}
      >
        <span className={cn('absolute left-0 top-0 bottom-0 w-1.5 rounded-l-xl', urgency.bar)}
              aria-hidden />

        <div className="w-20 sm:w-28 shrink-0 flex flex-col justify-center">
          <span className={cn('inline-flex items-center gap-1 self-start px-2 py-0.5 rounded-full text-[11px] font-semibold border',
                              urgency.badge)}>
            <Clock className="w-3 h-3" aria-hidden />
            {urgency.label}
          </span>
          <span className="mt-1 text-lg font-semibold text-gray-900 tabular-nums">
            {formatWait(seconds)}
          </span>
          <span className="text-[11px] text-gray-500">na fila humana</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-gray-400 tabular-nums">#{position}</span>
            <h4 className="font-semibold text-gray-900 truncate">{conversation.customer_name}</h4>
            <Icon className="w-4 h-4 text-gray-400 shrink-0" aria-label={conversation.channel} />
            {conversation.unread && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">
                Aguardando resposta
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 truncate mt-0.5">{conversation.last_message}</p>
          <div className="flex items-center gap-2 flex-wrap mt-2 text-xs">
            {priority && (
              <span className={cn('px-2 py-0.5 rounded-full font-medium', priority.className)}>
                {priority.label}
              </span>
            )}
            {conversation.intent && (
              <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                {conversation.intent}
              </span>
            )}
            <span className="text-gray-500">{conversation.area}</span>
            {sentiment && (
              <span className={cn('px-2 py-0.5 rounded-full border font-medium', sentiment.pill)}
                    title={`Sentimento detectado: ${sentiment.description}`}>
                <span aria-hidden>{sentiment.emoji}</span> {sentiment.label}
              </span>
            )}
            <span className="text-gray-400">· {conversation.message_count} mensagens</span>
          </div>
        </div>

        <div className="hidden sm:flex flex-col items-end justify-center gap-1 shrink-0 text-xs">
          {conversation.assigned_agent ? (
            <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium',
                                mine ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600')}>
              <UserCheck className="w-3 h-3" aria-hidden />
              {mine ? 'Com você' : conversation.assigned_agent}
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded-full bg-violet-50 text-violet-700 font-medium">
              Sem atendente
            </span>
          )}
          <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-[#E10019] transition-colors"
                        aria-hidden />
        </div>
      </Link>
    </li>
  );
}
