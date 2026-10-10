import { Bot, Headset, Info, Loader2, User } from 'lucide-react';

import { useConversation } from '../../api/hooks';
import type { ConversationHistoryItem, Message } from '../../api/types';
import MessageSentimentBadge from '../sentiment/MessageSentimentBadge';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '../ui/dialog';
import { cn } from '../ui/utils';
import { formatDate } from './historyStyles';

/**
 * Transcrição completa de uma conversa da linha do tempo, sem sair da tela
 * onde o atendente está trabalhando.
 */
export default function ConversationHistoryModal({ item, onClose }: {
  item: ConversationHistoryItem | null; onClose: () => void;
}) {
  return (
    <Dialog open={item !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col bg-white">
        {item && <Body item={item} />}
      </DialogContent>
    </Dialog>
  );
}

function Body({ item }: { item: ConversationHistoryItem }) {
  const state = useConversation(item.id);

  return (
    <>
      <DialogHeader>
        <DialogTitle>
          {item.type_label} · {formatDate(item.date)}
        </DialogTitle>
        <DialogDescription>
          {item.status_label}
          {item.intent && ` · ${item.intent}`}
          {item.nps_score != null && ` · NPS ${item.nps_score}`}
        </DialogDescription>
      </DialogHeader>

      <div className="flex-1 overflow-y-auto -mx-2 px-2 space-y-3 bg-gray-50 rounded-lg py-3">
        {state.loading && !state.data && (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin" /> Carregando a transcrição…
          </div>
        )}
        {state.error && !state.data && (
          <p className="text-sm text-red-700 text-center py-10">{state.error}</p>
        )}
        {state.data?.messages.map((message) => (
          <TranscriptMessage key={message.id} message={message} />
        ))}
        {state.data && state.data.messages.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-10">Conversa sem mensagens.</p>
        )}
      </div>
    </>
  );
}

function TranscriptMessage({ message }: { message: Message }) {
  if (message.author === 'system') {
    return (
      <p className="flex items-center justify-center gap-1.5 text-xs text-blue-800">
        <Info className="w-3.5 h-3.5" aria-hidden /> {message.text}
      </p>
    );
  }
  const customer = message.author === 'customer';
  const Icon = customer ? User : message.author === 'agent' ? Headset : Bot;
  const who = customer ? 'Cliente' : message.author === 'agent' ? 'Atendente' : 'Assistente';

  return (
    <div className={cn('flex', customer ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm relative',
        customer ? 'bg-[#E10019] text-white'
          : message.author === 'agent' ? 'bg-emerald-600 text-white'
          : 'bg-white border border-gray-200 text-gray-900')}>
        <p className="whitespace-pre-wrap">{message.text}</p>
        <p className={cn('flex items-center gap-1 mt-1 text-[11px]',
                         customer || message.author === 'agent' ? 'text-white/70' : 'text-gray-400')}>
          <Icon className="w-3 h-3" aria-hidden /> {who} ·{' '}
          {new Date(message.timestamp).toLocaleString('pt-BR',
            { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
        </p>
        {customer && message.sentiment && (
          <span className="absolute -left-2 -bottom-2">
            <MessageSentimentBadge sentiment={message.sentiment} />
          </span>
        )}
      </div>
    </div>
  );
}
