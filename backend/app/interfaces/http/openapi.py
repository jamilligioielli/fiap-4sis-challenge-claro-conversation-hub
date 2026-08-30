"""Metadados da especificação OpenAPI.

A documentação é parte da entrega, não um subproduto: a promessa da solução é que
um canal novo se integra sem tocar no núcleo, e isso só é verdade se o contrato
estiver legível para quem vai escrever o próximo adaptador.

Os endpoints estão separados em duas famílias, e a distinção é intencional:

  * **Ingestão** — o que os canais chamam para *entregar* interações ao hub.
  * **Console**  — o que o front-end chama para *ler e operar* o que o hub processou.

Um time que vai plugar um canal novo só precisa ler a primeira família.
"""

DESCRIPTION = """
Camada de orquestração conversacional da Claro. Recebe interações de qualquer
canal digital, classifica a intenção, mantém o contexto do cliente entre canais,
aciona os sistemas internos e aplica a persona da marca — para que o cliente
perceba **uma só Claro** em qualquer ponto de contato.

## Como as duas famílias de endpoints se relacionam

```
  WhatsApp ─┐
  Web Chat ─┼─▶  POST /api/v1/channels/{canal}/messages   (ingestão)
  App      ─┤                     │
  URA      ─┘                     ▼
                        [ núcleo conversacional ]
                                  │
                                  ▼
     GET /api/v1/conversations, /customers, /dashboard, /studio   (console)
                                  │
                                  ▼
                        Console de Operação (React)
```

## Integrando um canal novo

1. Escreva um adaptador que traduza o formato do seu canal para o corpo de
   `POST /api/v1/channels/{canal}/messages`.
2. Envie `external_id` — o identificador do cliente *naquele canal* (telefone,
   cookie, device id). O hub resolve para o `customer_id`, que é a chave real
   da memória. É isso que faz a conversa sobreviver à troca de canal.
3. Envie o `consent` do cliente para aquele canal. Sem consentimento para a
   finalidade `atendimento`, o hub recusa a interação (HTTP 403).
4. Responda ao cliente com o campo `reply` que voltar.

Nenhum passo acima exige alteração no núcleo do hub.

## Requisitos funcionais e onde estão

| RF | Requisito | Onde se observa |
|----|-----------|-----------------|
| RF001 | Receber interação de canal | `POST /channels/{canal}/messages` — qualquer canal produz o mesmo evento interno |
| RF002 | Identificar intenção | Campo `intent` da resposta, com `confidence` e `engine` |
| RF003 | Persistir contexto | `context_recovered` e `context_note` ao trocar de canal |
| RF004 | Rotear por intenção | Campos `flow` e `services_consulted` |
| RF005 | Transferir para humano | `handover_triggered` e `POST /conversations/{id}/handover` |
| RF006 | Aplicar persona | Campo `persona_applied`; configuração em `/studio` |

## Motor de intenção

O hub fala o protocolo OpenAI (`/chat/completions`), não um provedor específico.
Configure `LLM_BASE_URL`, `LLM_MODEL` e `LLM_API_KEY` para usar Groq, Google AI
Studio, OpenAI, OpenRouter ou um modelo local.

**Sem chave configurada o hub continua funcionando**: cai para um classificador
determinístico por palavra-chave. O campo `intent.engine` (`llm` ou `rules`) diz
qual dos dois respondeu — a interface mostra isso, e nenhuma demonstração depende
de rede.

## LGPD

O consentimento viaja dentro do próprio evento, e todo acesso a dado de cliente
é registrado na trilha de auditoria (`GET /api/v1/audit`).
"""

TAGS: list[dict] = [
    {
        "name": "Ingestão de Canais",
        "description": (
            "**Chamados pelos canais.** Ponto de entrada único de todas as interações. "
            "É a única família de endpoints que um time precisa conhecer para plugar "
            "um canal novo no hub."
        ),
    },
    {
        "name": "Console · Conversas",
        "description": (
            "**Chamados pelo front-end.** Fila do Inbox, transcrição da Conversa Ativa, "
            "painel de IA, transferência para atendente e resposta do agente."
        ),
    },
    {
        "name": "Console · Clientes",
        "description": (
            "**Chamados pelo front-end.** Visão 360° que alimenta a tela de Contexto do "
            "Cliente: perfil, plano, produtos, histórico entre canais e elegibilidade."
        ),
    },
    {
        "name": "Console · Dashboard",
        "description": (
            "**Chamados pelo front-end.** Métricas derivadas das conversas que o hub "
            "realmente processou — não de constantes. Mandar uma mensagem por um canal "
            "move o número na tela."
        ),
    },
    {
        "name": "Console · Design Studio",
        "description": (
            "**Chamados pelo front-end.** Configuração da persona, das intenções, dos "
            "guardrails e do tom de voz por canal. Salvar aqui muda o comportamento de "
            "todos os canais na próxima mensagem, sem deploy."
        ),
    },
    {
        "name": "Operação",
        "description": "Saúde do serviço, modo de operação dos componentes e trilha de auditoria.",
    },
]

CONTACT = {"name": "Time Labware — FIAP 4SIS", "url": "https://github.com/"}
LICENSE = {"name": "Uso acadêmico — Challenge FIAP 2026"}

SERVERS = [
    {"url": "http://localhost:8000", "description": "Ambiente local (Docker Compose)"},
]
