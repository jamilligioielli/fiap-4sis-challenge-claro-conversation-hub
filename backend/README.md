# Claro Conversation Hub — Back-end

API da camada de orquestração conversacional. FastAPI + arquitetura limpa.

## Subir

```bash
cp ../.env.example ../.env       # opcional: só para configurar a IA
docker compose up --build        # a partir da raiz do projeto
```

Documentação interativa em **http://localhost:8000/docs** (Swagger UI). Especificação crua em `/openapi.json`.

Sem Docker:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Sem Redis e sem MongoDB o hub sobe do mesmo jeito, em memória. O `/health` diz
em que modo cada componente está. É proposital: numa apresentação com prazo, um
container que não levantou não pode derrubar a demonstração.

## Motor de intenção

O hub fala o **protocolo OpenAI** (`POST /chat/completions`), não um provedor.
Configure três variáveis:

```bash
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
LLM_API_KEY=gsk_...
```

Outros provedores compatíveis, trocando apenas essas variáveis:

| Provedor | `LLM_BASE_URL` | Gratuito |
|---|---|---|
| Groq | `https://api.groq.com/openai/v1` | sim, sem cartão |
| Google AI Studio | `https://generativelanguage.googleapis.com/v1beta/openai` | sim, com limites |
| GitHub Models | `https://models.inference.ai.azure.com` | sim, para contas GitHub |
| OpenRouter | `https://openrouter.ai/api/v1` | modelos `:free` |
| OpenAI | `https://api.openai.com/v1` | não |
| Ollama (local) | `http://localhost:11434/v1` | sim, roda na máquina |

**Sem `LLM_API_KEY` o hub continua funcionando**: assume o classificador
determinístico por palavra-chave. O campo `intent.engine` de cada resposta diz
qual dos dois respondeu (`llm` ou `rules`), e a interface mostra isso.

## Arquitetura

```
app/
├── domain/                    regras de negócio — não importa nada de fora
│   ├── value_objects.py       Channel, Area, Intent, Consent
│   ├── entities.py            Conversation (agregado raiz), Customer, Session
│   ├── studio.py              configuração da persona
│   ├── ports.py               interfaces que a infraestrutura implementa
│   └── services/              regras puras, sem I/O
│       ├── identity_service.py      resolução de identidade entre canais
│       ├── routing_service.py       RF004 — decide o fluxo
│       ├── persona_service.py       RF006 — aplica o tom de voz
│       ├── reply_composer.py        conteúdo da resposta de negócio
│       ├── handover_policy.py       RF005 — quando sair do bot
│       └── intent_continuity.py     herança de assunto entre turnos
│
├── application/use_cases/     orquestra o domínio; fala só com as portas
│   ├── ingest_message.py      RF001→RF006 em uma transação de conversa
│   ├── console.py             Inbox, Conversa Ativa, handover, resposta do agente
│   ├── customer_context.py    visão 360°
│   ├── dashboard.py           métricas derivadas das conversas reais
│   └── studio_config.py       persona e tom de voz
│
├── infrastructure/            adaptadores — implementam as portas
│   ├── persistence/           memory · redis_session · mongo
│   ├── llm/                   openai_compatible · rule_based · prompt_loader
│   ├── integrations/          sistemas internos da Claro (mocks)
│   └── seed.py                dados da demonstração
│
├── prompts/                   texto enviado ao modelo — nada em código Python
├── interfaces/http/           routers, DTOs e metadados OpenAPI
├── container.py               composition root — onde tudo é ligado
└── main.py                    monta o FastAPI
```

A dependência aponta sempre para dentro: `interfaces → application → domain`, e
`infrastructure → domain`. O domínio não importa FastAPI, Redis, Mongo nem httpx —
por isso os testes de regra rodam sem subir nada.

## Endpoints

Separados em duas famílias, e a distinção importa:

**Ingestão** — o que os canais chamam. É tudo o que um time precisa para plugar
um canal novo.

```
POST /api/v1/channels/{canal}/messages
GET  /api/v1/channels
```

**Console** — o que o front-end chama para ler e operar.

```
GET   /api/v1/conversations                        fila do Inbox
                                                   ?transferred_only=true → fila do atendente
GET   /api/v1/conversations/{id}                   transcrição + painel de IA
POST  /api/v1/conversations/{id}/handover          transferir (RF005)
POST  /api/v1/conversations/{id}/messages          responder como atendente
GET   /api/v1/customers/{id}/context               visão 360°
GET   /api/v1/customers/{id}/conversation-history  linha do tempo + indicadores (Sprint 4)
GET   /api/v1/dashboard                            métricas
GET   /api/v1/dashboard/nps-comparison             NPS bot × atendente (Sprint 4)
GET   /api/v1/studio/config                        persona e tom de voz
PUT   /api/v1/studio/config
PATCH /api/v1/studio/channels/{canal}
GET   /health · /api/v1/audit · /api/v1/prompts
```

## Testes

```bash
pytest
```

Cobrem as regras de domínio: persona, roteamento, política de transbordo,
continuidade de intenção e as invariantes do agregado Conversation — e, desde a
Sprint 4, o comparativo de NPS, a fila do atendente, a detecção de sentimento,
o histórico do cliente e os dados de demonstração.

## Dados de demonstração

`DEMO_SEED=true` cria, ao subir, conversas de exemplo para as melhorias da
Sprint 4. Com MongoDB, `python -m scripts.seed_demo [--reset|--clear]`.

## Prompts

Todo texto enviado ao modelo vive em `app/prompts/*.md`, fora do código. O
Compose monta essa pasta como volume: editar um prompt não exige rebuild.
Veja `app/prompts/README.md`.
