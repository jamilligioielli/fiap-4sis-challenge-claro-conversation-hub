# Claro Conversation Hub

Camada de orquestração conversacional que unifica os canais digitais da Claro sob um mesmo motor de linguagem natural, um
mesmo contexto de cliente e uma mesma persona de marca.

Challenge FIAP 2026 · 4SIS · Equipe LABWARE · MVP (Fase 1)

---

## Subir o projeto

```bash
cp .env.example .env 
#Preencher o arquivo .env com as configs necessarias
docker compose up --build
```

| Serviço | Endereço |
|---|---|
| Console de operação | http://localhost:3000 |
| API — Swagger UI | http://localhost:8000/docs |
| API — ReDoc | http://localhost:8000/redoc |
| Especificação OpenAPI | http://localhost:8000/openapi.json |

Sem Docker:

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

**Sem Redis, sem MongoDB e sem chave de IA o sistema sobe e funciona.** Cai para
memória e para o classificador determinístico, e informa em que modo está no
`/health` e no rodapé do console. Numa apresentação com prazo, um container que
não levantou não pode derrubar a demonstração inteira.

---

## Percorrendo a demonstração

O caminho mais curto para ver os seis requisitos funcionando, em três minutos:

1. **Simulador de Canais** → escolha **Web Chat** e escreva
   *"Olá, gostaria de alterar meu plano para o Claro Flex 50GB"*.
   O painel da direita mostra a intenção classificada, a confiança, a entidade
   extraída, os sistemas internos consultados e a persona aplicada.
2. Troque o seletor para **WhatsApp** e escreva *"Estou pelo celular agora, pode
   prosseguir"*. O hub reconhece o mesmo cliente, avisa a migração de canal e
   **continua de onde parou** — não repete a oferta nem pede nada de novo.
   É o núcleo da proposta, e acontece em dois cliques.
3. Escreva *"Prefiro falar com um atendente"*. A conversa sai do bot com o
   histórico empacotado.
4. **Inbox** → a conversa está na fila, com resumo e prioridade.
   **Abrir conversa** → o atendente vê a transcrição inteira, o resumo automático
   e as próximas melhores ações. Responda como atendente.
5. Escreva mais alguma coisa no Simulador: a mensagem chega **nessa mesma
   conversa**, e o bot não fala por cima do atendente.
6. **Dashboard** → os números se moveram. Eles são calculados das conversas que
   o hub processou, não são constantes.
7. **Design Studio** → mude a formalidade do WhatsApp para 90 e salve. Volte ao
   Simulador: a Claro passa a falar diferente, sem deploy.

---

## Arquitetura

```
      WhatsApp ─┐
      Web Chat ─┼──▶  POST /api/v1/channels/{canal}/messages     (ingestão)
      App      ─┤                       │
      URA      ─┘                       ▼
                          ┌─────────────────────────────┐
                          │   NÚCLEO CONVERSACIONAL     │
                          │  intenção · contexto ·      │
                          │  roteamento · persona ·     │
                          │  handover                   │
                          └──────┬───────────────┬──────┘
                                 │               │
                     Redis (sessão)   MongoDB (histórico por cliente)
                                 │               │
                                 ▼               ▼
                    Sistemas internos da Claro (simulados)
                                 │
                                 ▼
        GET /api/v1/conversations · /customers · /dashboard · /studio
                                 │
                                 ▼
                  Console de Operação (React + TypeScript)
```

### Camadas do back-end

```
backend/app/
├── domain/           regras de negócio — não importa nada de fora
├── application/      casos de uso; falam só com as portas do domínio
├── infrastructure/   adaptadores: Redis, Mongo, LLM, WhatsApp, mocks
├── prompts/          texto enviado ao modelo — nada em código Python
└── interfaces/http/  routers, DTOs e metadados OpenAPI
```

A dependência aponta sempre para dentro. O domínio não conhece FastAPI, Redis,
Mongo nem httpx — por isso os testes de regra rodam em 0,1s sem subir nada.

`container.py` é o único arquivo que escolhe implementações concretas. Trocar
MongoDB por Postgres, ou Groq por OpenAI, é editar aquele arquivo.

### Decisão que sustenta tudo

A memória é indexada pelo **`customer_id`**, nunca pelo identificador do canal.
O telefone do WhatsApp, o cookie do site e o device id do app são apelidos que
resolvem para ele. Sem essa decisão, cada canal teria a própria sessão — e o
cliente continuaria percebendo "várias Claros".

---

## Requisitos funcionais

| RF | Requisito | Onde se observa |
|----|-----------|-----------------|
| RF001 | Receber interação de canal | `POST /channels/{canal}/messages` — qualquer canal produz o mesmo evento interno |
| RF002 | Identificar intenção | Campo `intent`, com `confidence` e `engine` |
| RF003 | Persistir contexto | `context_recovered` e `context_note` ao trocar de canal |
| RF004 | Rotear por intenção | Campos `flow` e `services_consulted` |
| RF005 | Transferir para humano | `handover_triggered` e `POST /conversations/{id}/handover` |
| RF006 | Aplicar persona | Campo `persona_applied`; configuração em `/studio` |

| RNF | Requisito | Como é atendido |
|----|-----------|-----------------|
| RNF001 | Disponibilidade | Fallback por componente; `/health` reporta o modo de operação |
| RNF002 | Escalabilidade | Núcleo sem estado; todo contexto em Redis e MongoDB |
| RNF003 | LGPD | Consentimento dentro do evento, trilha de auditoria, mascaramento |
| RNF004 | Manutenibilidade | Contrato único de evento; canal novo é um adaptador |
| RNF005 | Usabilidade | Linguagem natural, memória entre canais, sem repetição de dados |

---

## Motor de intenção

O hub fala o **protocolo OpenAI** (`/chat/completions`), não um provedor. Trocar
de IA é trocar três variáveis no `.env`:

```bash
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
LLM_API_KEY=gsk_...
```

Groq, Google AI Studio, GitHub Models, OpenRouter, OpenAI e Ollama local
funcionam sem alteração de código. **Sem chave, o classificador determinístico
assume** e o campo `intent.engine` diz qual dos dois respondeu.

Todo prompt vive em `backend/app/prompts/*.md`, versionado como conteúdo e
montado como volume no Compose — editar um prompt não exige rebuild.

---

## Canal WhatsApp (Cloud API)

Integração real com a WhatsApp Business Cloud API, com webhook de entrada,
envio de saída e validação de assinatura HMAC SHA-256.

```
GET  /api/v1/channels/whatsapp/webhook    handshake de verificação da Meta
POST /api/v1/channels/whatsapp/webhook    recebe mensagens (RF001)
GET  /api/v1/channels/whatsapp/status     diagnóstico da configuração
POST /api/v1/channels/whatsapp/send       envio de teste
```

O `.env.example` traz o passo a passo de onde obter cada credencial no painel da
Meta. O painel do Simulador mostra o que está configurado, o que falta e a URL
exata do webhook — sem exibir token nenhum.

Enquanto `WHATSAPP_ENABLED=false`, o canal funciona pelo simulador embutido, o
que já demonstra todos os requisitos funcionais.

---

## Testes

```bash
cd backend && pytest
```

22 testes das regras de domínio: persona, roteamento, política de transbordo,
continuidade de intenção e invariantes do agregado `Conversation`.

---

## Estrutura

```
claro-hub/
├── docker-compose.yml      redis · mongo · api · web
├── .env.example            todas as variáveis, documentadas
├── backend/                FastAPI · arquitetura limpa
│   ├── app/
│   ├── tests/
│   └── README.md           detalhes do back-end
└── frontend/               React · TypeScript · Vite · Tailwind
    ├── src/app/api/        cliente HTTP e hooks — única parte que conhece a API
    ├── src/app/pages/      Dashboard · Inbox · Conversa · Contexto · Studio · Simulador
    └── Dockerfile          build + nginx com proxy para a API
```
