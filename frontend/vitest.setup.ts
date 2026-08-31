import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// jsdom não implementa scrollIntoView, e o simulador chama isso a cada mensagem.
Element.prototype.scrollIntoView = vi.fn();

// Nem ResizeObserver, que os gráficos do dashboard usam para se redimensionar.
// Sem isto o Recharts derruba a árvore inteira e o teste falha por um motivo
// que não tem nada a ver com o que ele está verificando.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);

// O ResponsiveContainer mede o elemento pai; em jsdom tudo mede zero e nada é
// desenhado. Damos uma caixa fixa para que os gráficos rendereizem no teste.
Object.defineProperty(HTMLElement.prototype, 'offsetWidth',
  { configurable: true, value: 800 });
Object.defineProperty(HTMLElement.prototype, 'offsetHeight',
  { configurable: true, value: 400 });
