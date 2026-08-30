import { AlertTriangle, Loader2, Inbox as InboxIcon } from 'lucide-react';
import type { ReactNode } from 'react';

/**
 * Estados de carregamento, erro e vazio.
 *
 * Existem como componente próprio porque toda tela que fala com a API precisa
 * dos três, e porque a mensagem de erro precisa dizer o que fazer — "Erro"
 * sozinho não ajuda ninguém a resolver nada.
 */

export function Loading({ label = 'Carregando…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
      <Loader2 className="w-7 h-7 animate-spin mb-3 text-[#E10019]" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const unreachable = message.includes('alcançar');
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <AlertTriangle className="w-6 h-6 text-[#E10019]" />
      </div>
      <h3 className="text-base font-semibold text-gray-900 mb-1">
        {unreachable ? 'API do hub indisponível' : 'Não foi possível carregar'}
      </h3>
      <p className="text-sm text-gray-600 max-w-md mb-4">{message}</p>
      {unreachable && (
        <p className="text-xs text-gray-500 max-w-md mb-4">
          Verifique se o back-end está rodando em <code className="px-1 bg-gray-100 rounded">
          http://localhost:8000</code> — <code className="px-1 bg-gray-100 rounded">
          docker compose up</code> na raiz do projeto.
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-[#E10019] text-white rounded-lg text-sm font-medium hover:bg-[#C20015] transition-colors"
        >
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description, icon }: {
  title: string; description?: string; icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="mb-3 text-gray-300">
        {icon ?? <InboxIcon className="w-12 h-12" />}
      </div>
      <h3 className="text-base font-medium text-gray-900 mb-1">{title}</h3>
      {description && <p className="text-sm text-gray-600 max-w-sm">{description}</p>}
    </div>
  );
}

export function AsyncBoundary<T>({ state, children, loadingLabel, empty }: {
  state: { data: T | null; error: string | null; loading: boolean; reload: () => void };
  children: (data: T) => ReactNode;
  loadingLabel?: string;
  empty?: ReactNode;
}) {
  if (state.loading && state.data === null) return <Loading label={loadingLabel} />;
  if (state.error && state.data === null) {
    return <ErrorState message={state.error} onRetry={state.reload} />;
  }
  if (state.data === null) return <>{empty ?? <EmptyState title="Nada por aqui" />}</>;
  return <>{children(state.data)}</>;
}
