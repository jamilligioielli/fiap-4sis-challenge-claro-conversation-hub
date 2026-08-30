import { BrowserRouter, Routes, Route, Navigate } from 'react-router';

import Layout from './components/Layout';
import ChannelSimulator from './pages/ChannelSimulator';
import Conversation from './pages/Conversation';
import CustomerContext from './pages/CustomerContext';
import Dashboard from './pages/Dashboard';
import DesignStudio from './pages/DesignStudio';
import Inbox from './pages/Inbox';

/**
 * Rotas do console.
 *
 * `/conversation/:id` e `/customer-context/:id` passaram a receber o id na URL:
 * com os dados vindo da API, cada conversa e cada cliente têm endereço próprio
 * — o que o protótipo, com uma tela fixa por rota, não tinha.
 */
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="inbox" element={<Inbox />} />
          <Route path="simulator" element={<ChannelSimulator />} />
          <Route path="conversation/:id" element={<Conversation />} />
          <Route path="customer-context/:id" element={<CustomerContext />} />
          <Route path="design-studio" element={<DesignStudio />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
