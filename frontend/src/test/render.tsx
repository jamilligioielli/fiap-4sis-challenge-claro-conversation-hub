import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';

/**
 * Renderiza um componente dentro de um roteador de memória.
 *
 * Quase toda tela do console usa `Link` ou `useParams`; renderizar sem roteador
 * quebraria por um motivo que não tem nada a ver com o que se quer testar.
 */
export function renderAt(
  ui: ReactElement,
  { path = '/', route = '/' }: { path?: string; route?: string } = {},
) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path={path} element={ui} />
        <Route path="*" element={ui} />
      </Routes>
    </MemoryRouter>,
  );
}
