# Prompts do Claro Conversation Hub

Todo texto enviado ao modelo de linguagem mora aqui — **nenhum prompt é escrito
dentro do código Python**. A separação existe por três motivos:

1. **Quem ajusta o prompt não precisa mexer no código.** Design conversacional é
   trabalho de quem cuida da linguagem da marca.
2. **Prompt entra no controle de versão como conteúdo**, revisável num diff legível.
3. **Trocar de provedor de IA não reescreve o prompt.** O adaptador muda; o texto fica.

## Como funciona

Os arquivos são carregados por `infrastructure/llm/prompt_loader.py`, que substitui
variáveis no formato `{{variavel}}`. Em desenvolvimento o arquivo é relido a cada
chamada — dá para editar o prompt e ver o efeito sem reiniciar a API.

## Arquivos

| Arquivo | Usado em | Variáveis principais |
|---|---|---|
| `response_generation.md` | Redação de toda resposta ao cliente | `{{persona_nome}}`, `{{guardrails}}`, `{{canal}}`, `{{formalidade}}`, `{{cliente}}`, `{{fatos}}`, `{{historico}}`, `{{mensagem}}`, `{{objetivo}}` |
| `intent_classification.md` | Classificação da intenção | `{{intencoes}}`, `{{historico}}`, `{{texto}}` |
| `conversation_summary.md` | Resumo para o atendente | `{{transcricao}}` |
| `next_best_actions.md` | Sugestões de próxima ação | `{{transcricao}}`, `{{contexto_cliente}}` |

## Por que um único prompt de conversa

Saudação de abertura, resposta a uma dúvida, pergunta de continuidade ao trocar de
canal e abordagem ativa são situações diferentes — mas a *identidade* de quem fala é
a mesma em todas. Manter um prompt e variar apenas o campo `{{objetivo}}` garante
que a persona, os guardrails e o tom do canal sejam idênticos nos quatro casos.
Quatro prompts separados dariam quatro personas ligeiramente diferentes, que é
exatamente o problema que esta solução existe para resolver.

## Regras ao editar

- Mantenha a instrução de "responda apenas com o texto da mensagem": o código não
  faz interpretação, só limpa aspas e markdown residual.
- Os guardrails vêm do Design Studio e são injetados em `{{guardrails}}`. Não os
  duplique aqui — o lugar deles é o Studio, onde a operação consegue editá-los.
- Se o modelo passar a devolver algo fora do esperado, o hub cai automaticamente
  para o redator determinístico. Prompt ruim degrada a qualidade, não derruba o sistema.
