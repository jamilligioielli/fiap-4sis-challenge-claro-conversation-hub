# Claro Conversation Hub

Camada de orquestração conversacional (gerenciamento de workflow de atendimento) que unifica os canais digitais da Claro sob um mesmo motor de linguagem natural, um
mesmo contexto de cliente e uma mesma persona de marca.

Challenge FIAP 2026 · 4SIS · Time Labware · MVP (Fase 1)

---

## Subir o projeto

```bash
cp .env.example .env      # opcional — o hub sobe sem nenhuma configuração
docker compose up --build
```

| Serviço | Endereço |
|---|---|
| Console de operação e Simulador| http://localhost:3000 |
| API — Swagger UI | http://localhost:8000/docs |

Sem Docker:

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

**Sem Redis, sem MongoDB e sem chave de IA o sistema sobe e funciona.** Cai para
memória e para o classificador determinístico, e informa em que modo está no
`/health` no rodapé do console de admin.

---

## O que a solução faz, e onde isso se observa

| Capacidade | Onde se observa |
|------------|-----------------|
| Recebe a interação de qualquer canal | `POST /channels/{canal}/messages` — todo canal produz o mesmo evento interno |
| Entende o que o cliente quer | Campo `intent`, com `confidence` e `engine` |
| Lembra do cliente entre canais | `context_recovered` e `context_note`; ao trocar de canal, `awaiting_context_confirmation` |
| Encaminha para o fluxo de negócio certo | Campos `flow` e `services_consulted` |
| Passa para um humano quando precisa | `handover_triggered` e `POST /conversations/{id}/handover` |
| Fala na voz da marca | `persona_applied` e `persona_version`; configuração em `/studio` |
| Escreve a resposta na hora | `response_source` (`generative` ou `template`) e `response_model` |
| Também inicia a conversa | `GET /outreach/eligible` e `POST /outreach/send`, respeitando consentimento e janela de 24h |

| Qualidade | Como é atendida |
|-----------|-----------------|
| Disponibilidade | Fallback por componente; `/health` reporta o modo de operação de cada um |
| Escalabilidade | Núcleo sem estado; todo contexto em Redis e MongoDB |
| Privacidade (LGPD) | Consentimento dentro do evento, trilha de auditoria, mascaramento de documento |
| Manutenibilidade | Contrato único de evento; canal novo é um adaptador, não uma alteração no núcleo |
| Usabilidade | Linguagem natural, memória entre canais, nenhum dado pedido duas vezes |

---

## Motor de intenção

O hub fala o **protocolo OpenAI** (`/chat/completions`), não um provedor. Trocar
de IA é trocar três variáveis no `.env`:

```bash
LLM_BASE_URL=...
LLM_MODEL=...
LLM_API_KEY=...
```

### Compatibilidade com modelos de raciocínio

`gpt-oss`, `qwen` e `deepseek-r1` por exemplo devolvem o raciocínio junto da resposta se
ninguém pedir o contrário — e monólogo interno de robô não chega a cliente. O
campo que desliga isso varia por provedor, então ele vem da configuração e não
do código, exemplo:

```bash
LLM_EXTRA_PARAMS={"include_reasoning": false, "reasoning_effort": "low"}
```

O que estiver nessa variável é fundido no corpo da requisição. É assim que o
cliente HTTP continua falando só o protocolo, sem nunca saber o nome de um
provedor. Como rede de segurança, `clean_reply` ainda remove blocos `<think>` e
o formato *harmony* caso algum escape — entre o cliente ler o raciocínio do robô
e uma expressão regular a mais, a escolha é fácil.

Groq, Google AI Studio, GitHub Models, OpenRouter, OpenAI e Ollama local
funcionam sem alteração de código. **Sem chave, o classificador determinístico
assume** e o campo `intent.engine` diz qual dos dois respondeu.

Todo prompt vive em `backend/app/prompts/*.md`, versionado como conteúdo e
montado como volume no Compose — editar um prompt não exige rebuild.

---

## Ritmo da conversa

Três comportamentos governam quando o assistente fala — e quando ele cala.

**Ele espera o cliente terminar de escrever.** Cada mensagem reinicia uma janela
de silêncio; o lote inteiro chega ao núcleo como um pedido só. "Oi, tudo bem?"
seguido de "é que a minha franquia acabou de novo" produz uma resposta, não
duas. A janela vem de `BOT_REPLY_DELAY_SECONDS` (30s por padrão) e o campo de
texto continua liberado durante a espera — travá-lo destruiria o propósito.
No contrato, a mensagem absorvida volta com `superseded: true`.

**Depois do transbordo, ele para de falar.** Nada de "sua mensagem foi
encaminhada": quem está com o caso é uma pessoa, e um robô comentando por cima é
ruído para os dois lados. As mensagens seguem chegando à transcrição, à vista do
atendente, e o campo `reply` volta vazio.

**Ao encerrar, dispara a pesquisa.** Vale para os dois caminhos — o assistente
reconhecendo uma despedida do cliente, ou o atendente clicando em *Encerrar
atendimento* no console. A conversa fica em espera até a nota chegar, o hub
insiste no máximo uma vez, e quem recusa é encerrado do mesmo jeito. O NPS do
painel passa a ser a fórmula real (promotores menos detratores), não um proxy.

```bash
BOT_REPLY_DELAY_SECONDS=30    # 5 a 8 para gravar o vídeo
NPS_ON_CLOSE=true
```

---

## Canal WhatsApp (Cloud API)

Integração real com a WhatsApp Business Cloud API, com webhook de entrada,
envio de saída e validação de assinatura HMAC SHA-256.

```
GET  /api/v1/channels/whatsapp/webhook    handshake de verificação da Meta
POST /api/v1/channels/whatsapp/webhook    recebe mensagens do cliente
GET  /api/v1/channels/whatsapp/status     diagnóstico da configuração
POST /api/v1/channels/whatsapp/send       envio de teste
```

O `.env.example` traz o passo a passo de onde obter cada credencial no painel da
Meta. O diagnóstico fica em `GET /api/v1/channels/whatsapp/status`, que responde
o que está configurado, o que falta e a URL exata do webhook — sem devolver token
nenhum. Ele é deliberadamente um endpoint de operação, e não uma tela: quem
simula um cliente não tem o que fazer com credencial de integração.

Enquanto `WHATSAPP_ENABLED=false`, o canal funciona pelo simulador embutido, que
já exercita a solução inteira de ponta a ponta.

### Contato ativo e a política da Meta

Quando é a Claro que inicia a conversa, duas regras da própria plataforma passam
a valer, e o hub as modela no domínio em vez de fingir envio irrestrito:

* **Consentimento explícito** do cliente para receber oferta.
* **Janela de 24 horas** desde a última mensagem dele. Dentro dela, a mensagem é
  livre; fora dela, só sai por modelo previamente aprovado pela Meta, na
  categoria correta (`utility`, `marketing` ou `authentication`).

`GET /api/v1/outreach/eligible` devolve, para cada cliente, o motivo da indicação
e — com o mesmo destaque — o que impede o contato. `POST /outreach/send` recusa o
envio enquanto o impedimento existir.

---

## Testes

```bash
cd backend && pip install -r requirements-dev.txt && pytest
cd frontend && npm install && npm test && npm run build
```
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

### Camadas do back-end

```
backend/app/
├── domain/           regras de negócio — não importa nada de fora
├── application/      casos de uso; falam só com as portas do domínio
├── infrastructure/   adaptadores: Redis, Mongo, LLM, WhatsApp, mocks
├── prompts/          texto enviado ao modelo
└── interfaces/http/  routers, DTOs e metadados OpenAPI
```