import { BrowserRouter, Routes, Route, Navigate } from 'react-router';

import ViewChooser from './pages/ViewChooser';
import CustomerPicker from './pages/simulator/CustomerPicker';
import SimulatorChat from './pages/simulator/SimulatorChat';
import ConsoleLayout from './pages/console/ConsoleLayout';
import Conversation from './pages/console/Conversation';
import CustomerContext from './pages/console/CustomerContext';
import Dashboard from './pages/console/Dashboard';
import DesignStudio from './pages/console/DesignStudio';
import Inbox from './pages/console/Inbox';
import Outreach from './pages/console/Outreach';

/**
 * Rotas.
 *
 * A árvore tem dois ramos porque a solução tem dois lados: `/simulador` é o
 * cliente sendo atendido, `/console` é a Claro atendendo. A raiz só escolhe
 * entre os dois — antes disso não há nada a ver.
 *
 * Dentro do console, conversa e cliente têm endereço próprio: com os dados
 * vindo da API, `/console/conversation/:id` é um link que se pode mandar para
 * alguém, o que o protótipo, com uma tela fixa por rota, não tinha.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ViewChooser />} />

        <Route path="/simulador" element={<CustomerPicker />} />
        <Route path="/simulador/:customerId" element={<SimulatorChat />} />

        <Route path="/console" element={<ConsoleLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="inbox" element={<Inbox />} />
          <Route path="contato-ativo" element={<Outreach />} />
          <Route path="conversation/:id" element={<Conversation />} />
          <Route path="customer-context/:id" element={<CustomerContext />} />
          <Route path="design-studio" element={<DesignStudio />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
