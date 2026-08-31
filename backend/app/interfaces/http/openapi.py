"""Metadados da especificação OpenAPI.

A documentação é parte da entrega, não um subproduto: a promessa da solução é que
um canal novo se integra sem tocar no núcleo, e isso só é verdade se o contrato
estiver legível para quem vai escrever o próximo adaptador.

Os endpoints estão separados em duas famílias, e a distinção é intencional:

  * **Ingestão** — o que os canais chamam para *entregar* interações ao hub.
  * **Console**  — o que o front-end chama para *ler e operar* o que foi processado.

Um time que vai plugar um canal novo só precisa ler a primeira família.
"""

DESCRIPTION = """
Camada de orquestração conversacional da Claro. Recebe interações de qualquer
canal digital, classifica a intenção, mantém o contexto do cliente entre canais,
aciona os sistemas internos e responde na voz da marca — para que o cliente
perceba **uma só Claro** em qualquer ponto de contato.

## Como as duas famílias se relacionam

```
  WhatsApp ─┐
  Web Chat ─┼─▶  POST /api/v1/channels/{canal}/messages   (ingestão)
  App      ─┤                     │
  URA      ─┘                     ▼
                        [ núcleo conversacional ]
                                  │
                                  ▼
   GET /conversations · /customers · /dashboard · /studio · /outreach   (console)
                                  │
                                  ▼
                        Console de Operação
```

## Integrando um canal novo

1. Escreva um adaptador que traduza o formato do seu canal para o corpo de
   `POST /api/v1/channels/{canal}/messages`.
2. Envie `external_id` — o identificador do cliente *naquele canal* (telefone,
   cookie, device id). O hub resolve para o identificador interno, que é a chave
   real da memória. É isso que faz a conversa sobreviver à troca de canal.
3. Envie o `consent` do cliente para aquele canal. Sem consentimento para a
   finalidade `atendimento`, o hub recusa a interação (HTTP 403).
4. Responda ao cliente com o campo `reply` que voltar.

Nenhum passo acima exige alteração no núcleo.

## Como as respostas são escritas

Com uma chave de modelo de linguagem configurada, **cada resposta é redigida na
hora**, considerando a persona do Design Studio, os guardrails, o tom do canal,
o perfil do cliente, o que os sistemas internos apuraram e tudo o que já foi dito
na conversa. Sem chave, um redator determinístico assume.

O campo `response_source` de cada resposta diz qual dos dois escreveu
(`generative` ou `template`), e `persona_version` diz qual versão da configuração
produziu aquele texto. Ninguém precisa acreditar na palavra do sistema.

## Continuidade entre canais

Quando o mesmo cliente reaparece em outro canal com um assunto em aberto, o hub
**não presume** que ele quer continuar: devolve `awaiting_context_confirmation` e
pergunta antes de agir. Decidir pelo cliente é o mesmo erro que a solução existe
para corrigir, só que ao contrário.

## Contato ativo

O hub também permite que a Claro inicie a conversa. Duas regras governam isso, e
ambas são verificadas no momento do envio: consentimento explícito para receber
oferta, e a janela de 24 horas desde a última mensagem do cliente — fora dela, o
contato só pode sair por modelo previamente aprovado.

## Privacidade

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
        "name": "Clientes",
        "description": (
            "Lista de clientes para simulação e visão consolidada para o console: "
            "perfil, plano, produtos, histórico entre canais e elegibilidade."
        ),
    },
    {
        "name": "Console · Conversas",
        "description": (
            "Fila de atendimento, transcrição, painel de apoio ao atendente, "
            "transferência e resposta do agente."
        ),
    },
    {
        "name": "Console · Dashboard",
        "description": (
            "Métricas derivadas das conversas que o hub realmente processou. O painel "
            "começa vazio de propósito: mandar uma mensagem por um canal é o que move "
            "o número na tela."
        ),
    },
    {
        "name": "Console · Design Studio",
        "description": (
            "Configuração da persona, das intenções, dos guardrails e do tom de voz por "
            "canal. Salvar aqui muda o comportamento de todos os canais na próxima "
            "mensagem, sem implantação. `POST /studio/preview` mostra o efeito antes."
        ),
    },
    {
        "name": "Console · Contato Ativo",
        "description": (
            "Quando a Claro inicia a conversa. Lista quem é elegível, com o motivo "
            "explícito e os impedimentos, e dispara a abordagem respeitando o "
            "consentimento e a janela de atendimento."
        ),
    },
    {
        "name": "Operação",
        "description": "Saúde do serviço, modo de operação dos componentes e auditoria.",
    },
]

CONTACT = {"name": "Time Labware — FIAP 4SIS", "url": "https://github.com/"}
LICENSE = {"name": "Uso acadêmico — Challenge FIAP 2026"}

SERVERS = [
    {"url": "http://localhost:8000", "description": "Ambiente local (Docker Compose)"},
]
