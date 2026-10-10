import type { ReactNode } from 'react';

import { cn } from '../ui/utils';

/**
 * Cartão do painel de contexto. Um assunto por cartão, título curto e ícone
 * colorido no topo — o atendente bate o olho e acha o que procura.
 */
export default function CustomerContextCard({ icon, title, accent = 'text-gray-500 bg-gray-50',
                                              children, action, className }: {
  icon: ReactNode;
  title: string;
  /** Classes de cor do ícone (texto e fundo). */
  accent?: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-label={title}
      className={cn('bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col min-w-0',
                    className)}
    >
      <header className="flex items-center gap-2 mb-3">
        <span className={cn('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', accent)}
              aria-hidden>
          {icon}
        </span>
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider flex-1">
          {title}
        </h4>
        {action}
      </header>
      <div className="flex-1 min-w-0 text-sm text-gray-700">{children}</div>
    </section>
  );
}
