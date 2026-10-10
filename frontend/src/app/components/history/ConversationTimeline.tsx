import { Bot, Headset } from 'lucide-react';

import type { ConversationHistoryItem } from '../../api/types';
import NpsHistoryBadge from '../context/NpsHistoryBadge';
import { cn } from '../ui/utils';
import { STATUS_STYLES, TYPE_STYLES, formatDate } from './historyStyles';

/**
 * Linha do tempo vertical das conversas do cliente, da mais recente para a
 * mais antiga. Cada ponto abre a transcrição completa.
 */
export default function ConversationTimeline({ items, onSelect, currentId }: {
  items: ConversationHistoryItem[];
  onSelect: (item: ConversationHistoryItem) => void;
  /** Conversa aberta na tela, destacada na linha do tempo. */
  currentId?: string;
}) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-6 text-center">
        Primeiro contato deste cliente — ainda não há conversas anteriores.
      </p>
    );
  }

  return (
    <ol className="relative" aria-label="Linha do tempo de conversas">
      {items.map((item, index) => {
        const status = STATUS_STYLES[item.status];
        const type = TYPE_STYLES[item.type] ?? TYPE_STYLES.suporte;
        const TypeIcon = type.icon;
        const StatusIcon = status.icon;
        const last = index === items.length - 1;
        const viewing = item.id === currentId;

        return (
          <li key={item.id} className="relative pl-8 pb-4">
            {!last && <span className="absolute left-[9px] top-5 bottom-0 w-0.5 bg-gray-200" aria-hidden />}
            <span className={cn('absolute left-0 top-1.5 w-5 h-5 rounded-full ring-4', status.dot)}
                  aria-hidden />
            <button
              type="button"
              onClick={() => onSelect(item)}
              aria-label={`Abrir conversa de ${formatDate(item.date)} — ${item.type_label}, ${item.status_label}`}
              className={cn('w-full text-left rounded-lg border p-3 transition-all hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-[#E10019]',
                            viewing ? 'border-[#E10019]/40 bg-red-50/40' : 'border-gray-200 bg-white hover:border-gray-300')}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold text-gray-900 tabular-nums">
                  {formatDate(item.date, true)}
                </span>
                <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-xs font-medium',
                                    type.className)}>
                  <TypeIcon className="w-3 h-3" aria-hidden />
                  {item.type_label}
                </span>
                {item.current && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#E10019] text-white font-semibold uppercase">
                    atual
                  </span>
                )}
              </div>
              {item.intent && item.intent !== item.type_label && (
                <p className="text-xs text-gray-600 mt-1 truncate">{item.intent}</p>
              )}
              <div className="flex items-center gap-2 flex-wrap mt-2">
                <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border',
                                    status.badge)}>
                  <StatusIcon className="w-3 h-3" aria-hidden />
                  {item.status_label}
                </span>
                {item.nps_score != null && (
                  <NpsHistoryBadge score={item.nps_score} category={item.nps_category} />
                )}
                <span className="ml-auto flex items-center gap-1 text-[11px] text-gray-400">
                  {item.attended_by === 'agent'
                    ? <><Headset className="w-3 h-3" aria-hidden /> humano</>
                    : <><Bot className="w-3 h-3" aria-hidden /> bot</>}
                  <span aria-hidden>·</span> {item.message_count} msg
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
