import { Link, Outlet, useLocation } from 'react-router';
import {
  LayoutDashboard, Inbox, MessageSquare, Palette, Megaphone, Cpu, Database,
  ArrowLeft,
} from 'lucide-react';

import { useHealth } from '../../api/hooks';
import { cn } from '../../components/ui/utils';

/**
 * Console de operação — o lado da Claro.
 *
 * O simulador saiu daqui de propósito. Este é o ambiente de quem atende, e
 * misturar nele a tela de quem é atendido embaralhava as duas leituras. O que
 * aparece nestas telas é consequência do que acontece do outro lado.
 */

const NAV = [
  { path: '/console', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { path: '/console/inbox', label: 'Inbox Omnichannel', icon: Inbox },
  { path: '/console/contato-ativo', label: 'Contato Ativo', icon: Megaphone },
  { path: '/console/design-studio', label: 'Design Studio', icon: Palette },
];

const TITLES: Record<string, string> = {
  '/console': 'Dashboard',
  '/console/inbox': 'Inbox Omnichannel',
  '/console/contato-ativo': 'Contato Ativo',
  '/console/design-studio': 'Conversation Design Studio',
};

export default function ConsoleLayout() {
  const location = useLocation();
  const health = useHealth();

  const title = TITLES[location.pathname]
    ?? (location.pathname.includes('/conversation/') ? 'Conversa Ativa'
      : location.pathname.includes('/customer-context/') ? 'Contexto do Cliente'
      : 'Claro Conversation Hub');

  const components = health.data?.components;
  const degraded = health.data?.status === 'degraded';

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#E10019] rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="font-semibold text-sm text-gray-900">Claro</div>
              <div className="text-xs text-gray-500">Console de Operação</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4">
          <div className="space-y-1">
            {NAV.map((item) => {
              const active = item.exact
                ? location.pathname === item.path
                : location.pathname.startsWith(item.path);
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    active ? 'bg-red-50 text-[#E10019]'
                           : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900',
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>

          <div className="mt-6 pt-4 border-t border-gray-100">
            <Link
              to="/"
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              <span>Trocar de visão</span>
            </Link>
          </div>
        </nav>

        {/* Estado real do back-end. Numa demonstração, saber em que modo o hub
            está rodando vale mais do que um rodapé decorativo. */}
        <div className="p-4 border-t border-gray-200 space-y-2">
          {components ? (
            <>
              <div className="flex items-center gap-2 text-xs">
                <span className={cn('w-2 h-2 rounded-full shrink-0',
                                    degraded ? 'bg-amber-500' : 'bg-green-500')} />
                <span className="text-gray-700 font-medium">
                  API {health.data?.status === 'ok' ? 'operacional' : 'em modo degradado'}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-gray-500">
                <Cpu className="w-3 h-3 shrink-0" />
                <span className="truncate" title={components.response_generator}>
                  {components.generative_ai ? 'respostas por IA generativa'
                                            : 'respostas por modelo de texto'}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-gray-500">
                <Database className="w-3 h-3 shrink-0" />
                <span className="truncate">
                  {components.history_store.includes('fallback') ? 'memória'
                                                                : 'MongoDB + Redis'}
                </span>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2 text-xs">
              <span className="w-2 h-2 rounded-full bg-gray-300 shrink-0" />
              <span className="text-gray-500">
                {health.error ? 'API indisponível' : 'verificando…'}
              </span>
            </div>
          )}
          <div className="text-[11px] text-gray-400 pt-1">
            Claro Brasil · MVP v{health.data?.version ?? '1.0.0'}
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
            <p className="text-xs text-gray-500">Claro Conversation Hub</p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm font-medium text-gray-900">Admin CX</div>
              <div className="text-xs text-gray-500">admin@claro.com.br</div>
            </div>
            <div className="w-10 h-10 rounded-full bg-[#E10019] flex items-center justify-center text-white font-medium">
              AC
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
