import { describe, expect, it, vi, beforeEach } from 'vitest';

import { api, ApiError } from './client';

/**
 * O cliente HTTP é o contrato entre as duas metades do projeto.
 *
 * Um caminho errado aqui não quebra a compilação nem aparece em revisão: aparece
 * na demonstração, com a tela em branco. Por isso o teste checa o que de fato
 * viaja — método, caminho e corpo — e não só que "a função existe".
 */

function mockFetch(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const spy = vi.fn().mockResolvedValue({
    ok: init.ok ?? true,
    status: init.status ?? 200,
    statusText: 'OK',
    json: async () => body,
  });
  vi.stubGlobal('fetch', spy);
  return spy;
}

beforeEach(() => vi.unstubAllGlobals());

describe('ingestão de canais', () => {
  it('entrega a mensagem no endpoint do canal informado', async () => {
    const fetchSpy = mockFetch({ conversation_id: 'conv1' });

    await api.sendAsCustomer('whatsapp', { text: 'oi', customer_id: 'cus1' });

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/v1/channels/whatsapp/messages');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ text: 'oi', customer_id: 'cus1' });
  });

  it('abre a conversa pedindo a saudação para o cliente e o canal escolhidos', async () => {
    const fetchSpy = mockFetch({ greeting: 'Oi!' });

    await api.startConversation('cus1', 'app');

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe('/api/v1/channels/conversations');
    expect(JSON.parse(init.body)).toEqual({ customer_id: 'cus1', channel: 'app' });
  });
});

describe('console', () => {
  it('monta a query string apenas com os filtros preenchidos', async () => {
    const fetchSpy = mockFetch([]);

    await api.listConversations({ area: 'Vendas', channel: undefined, search: '' });

    expect(fetchSpy.mock.calls[0][0]).toBe('/api/v1/conversations?area=Vendas');
  });

  it('não anexa query alguma quando não há filtro', async () => {
    const fetchSpy = mockFetch([]);

    await api.listConversations({});

    expect(fetchSpy.mock.calls[0][0]).toBe('/api/v1/conversations');
  });

  it('busca as conversas de um cliente específico', async () => {
    const fetchSpy = mockFetch([]);

    await api.listCustomerConversations('cus7');

    expect(fetchSpy.mock.calls[0][0]).toBe('/api/v1/customers/cus7/conversations');
  });

  it('pede o dashboard sem área quando nenhuma é escolhida', async () => {
    const fetchSpy = mockFetch({ has_data: false });

    await api.getDashboard(undefined);

    expect(fetchSpy.mock.calls[0][0]).toBe('/api/v1/dashboard');
  });
});

describe('contato ativo', () => {
  it('filtra por contactable somente quando pedido', async () => {
    const fetchSpy = mockFetch([]);

    await api.listEligibleCustomers();
    await api.listEligibleCustomers(true);

    expect(fetchSpy.mock.calls[0][0]).toBe('/api/v1/outreach/eligible');
    expect(fetchSpy.mock.calls[1][0]).toBe('/api/v1/outreach/eligible?only_contactable=true');
  });

  it('envia cliente, oferta e responsável na abordagem', async () => {
    const fetchSpy = mockFetch({ conversation_id: 'conv9' });

    await api.sendOutreach('cus1', 'offer-flex-50');

    expect(JSON.parse(fetchSpy.mock.calls[0][1].body)).toEqual({
      customer_id: 'cus1', offer_id: 'offer-flex-50', agent: 'Console',
    });
  });
});

describe('tratamento de erro', () => {
  it('distingue API fora do ar de API que respondeu erro', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')));

    await expect(api.getHealth()).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining('alcançar'),
    });
  });

  it('propaga o detail da API quando a resposta não é ok', async () => {
    mockFetch({ detail: 'Consentimento ausente' }, { ok: false, status: 403 });

    await expect(api.sendAsCustomer('web', { text: 'oi' })).rejects.toMatchObject({
      status: 403,
      message: 'Consentimento ausente',
    });
  });

  it('usa ApiError para que a tela possa reagir ao status', async () => {
    mockFetch({ detail: 'não encontrado' }, { ok: false, status: 404 });

    const error = await api.getConversation('inexistente').catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
  });
});
