import { Link } from 'react-router';
import {
  MessageSquare, Smartphone, LayoutDashboard, ArrowRight, Cpu, Database, Radio,
} from 'lucide-react';

import { useHealth } from '../api/hooks';
import { cn } from '../components/ui/utils';

/**
 * Porta de entrada.
 *
 * A solução tem dois lados que se olham: o cliente que é atendido e a equipe
 * que atende. Misturar os dois numa tela só — como estava antes — confunde quem
 * assiste, porque não fica claro de que lado da mesa se está em cada momento.
 */
export default function ViewChooser() {
  const health = useHealth();
  const components = health.data?.components;

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white flex flex-col">
      <header className="px-8 py-6">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-[#E10019] rounded-lg flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-semibold text-gray-900 leading-tight">Claro</div>
            <div className="text-xs text-gray-500 leading-tight">Conversation Hub</div>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 pb-16">
        <div className="w-full max-w-4xl">
          <div className="text-center mb-10">
            <h1 className="text-3xl font-bold text-gray-900 mb-3">
              De que lado da conversa você quer estar?
            </h1>
            <p className="text-gray-600 max-w-xl mx-auto">
              O mesmo hub atende os dois lados. Escolha uma visão para começar —
              o que você fizer de um lado aparece no outro.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <ViewCard
              to="/simulador"
              accent="bg-[#E10019]"
              hover="hover:border-[#E10019]"
              icon={<Smartphone className="w-6 h-6 text-white" />}
              title="Sou o cliente"
              subtitle="Simulador de canais"
              description={'Escolha uma persona e converse com a Claro pelo WhatsApp, '
                + 'pelo site ou pelo aplicativo. Troque de canal no meio da conversa '
                + 'e veja o que acontece.'}
              bullets={[
                'Personas com plano, histórico e perfil reais',
                'Conversas salvas — dá para voltar depois',
                'Mostra o que o hub fez a cada mensagem',
              ]}
            />

            <ViewCard
              to="/console"
              accent="bg-blue-600"
              hover="hover:border-blue-600"
              icon={<LayoutDashboard className="w-6 h-6 text-white" />}
              title="Sou a Claro"
              subtitle="Console de operação"
              description={'A visão de quem atende: fila de conversas, contexto do '
                + 'cliente, métricas da operação, configuração da persona e contato '
                + 'ativo com ofertas.'}
              bullets={[
                'Painel alimentado pelo que você simular',
                'Assumir conversas transferidas pelo assistente',
                'Mudar o tom de voz e ver o efeito na conversa',
              ]}
            />
          </div>

          {/* estado real do sistema — quem assiste merece saber em que modo está */}
          <div className="mt-8 flex items-center justify-center gap-6 text-xs text-gray-500 flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className={cn('w-2 h-2 rounded-full',
                health.data ? 'bg-green-500' : health.error ? 'bg-[#E10019]' : 'bg-gray-300')} />
              {health.data ? 'API conectada' : health.error ? 'API indisponível' : 'verificando…'}
            </span>
            {components && (
              <>
                <span className="flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5" />
                  {components.generative_ai
                    ? 'respostas escritas por IA generativa'
                    : 'respostas por modelo de texto'}
                </span>
                <span className="flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5" />
                  {components.history_store.includes('fallback') ? 'dados em memória'
                                                                 : 'MongoDB + Redis'}
                </span>
              </>
            )}
          </div>

          {components && !components.generative_ai && (
            <p className="mt-4 text-center text-xs text-gray-400 max-w-lg mx-auto">
              Sem uma chave de modelo de linguagem configurada, o assistente responde a
              partir de modelos de texto. Ele funciona, mas as respostas são menos
              naturais. Configure <code className="px-1 bg-gray-100 rounded">LLM_API_KEY</code> no
              arquivo <code className="px-1 bg-gray-100 rounded">.env</code> para ver a
              redação generativa.
            </p>
          )}
        </div>
      </main>
    </div>
  );
}

function ViewCard({ to, accent, hover, icon, title, subtitle, description, bullets }: {
  to: string; accent: string; hover: string; icon: React.ReactNode;
  title: string; subtitle: string; description: string; bullets: string[];
}) {
  return (
    <Link
      to={to}
      className={cn(
        'group block bg-white rounded-2xl border-2 border-gray-200 p-6 transition-all',
        'hover:shadow-lg', hover,
      )}
    >
      <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center mb-4', accent)}>
        {icon}
      </div>

      <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
      <p className="text-sm text-gray-500 mb-3">{subtitle}</p>
      <p className="text-sm text-gray-600 mb-4">{description}</p>

      <ul className="space-y-1.5 mb-5">
        {bullets.map((bullet) => (
          <li key={bullet} className="flex items-start gap-2 text-xs text-gray-600">
            <Radio className="w-3 h-3 mt-0.5 text-gray-300 shrink-0" />
            {bullet}
          </li>
        ))}
      </ul>

      <span className="inline-flex items-center gap-1.5 text-sm font-medium text-gray-900 group-hover:gap-2.5 transition-all">
        Entrar
        <ArrowRight className="w-4 h-4" />
      </span>
    </Link>
  );
}
