# Prompts do Claro Conversation Hub

Todo texto enviado ao modelo de linguagem externo mora aqui — **nenhum prompt é
escrito dentro do código Python**. Essa separação existe por três motivos:

1. **Quem ajusta o prompt não precisa mexer no código.** Design conversacional é
   trabalho de quem cuida da linguagem da marca, não de quem cuida da API.
2. **Prompt entra no controle de versão como conteúdo.** Dá para revisar a mudança
   de um prompt em um diff legível, sem ruído de sintaxe.
3. **Trocar de provedor de IA não reescreve o prompt.** O adaptador muda; o texto fica.

## Como funciona

Os arquivos são carregados por `infrastructure/llm/prompt_loader.py`, que faz
substituição simples de variáveis no formato `{{variavel}}`. Em produção o loader
mantém cache; em desenvolvimento (`ENVIRONMENT=development`) ele relê o arquivo a
cada chamada, então dá para editar o prompt e ver o efeito sem reiniciar a API.

```python
prompt = loader.render("intent_classification", texto=msg, intencoes=lista)
```

## Arquivos

| Arquivo | Usado em | Variáveis |
|---|---|---|
| `intent_classification.md` | RF002 — classificação de intenção | `{{intencoes}}`, `{{historico}}`, `{{texto}}` |
| `persona_system.md` | RF006 — instrução de sistema com a persona | `{{persona_nome}}`, `{{persona_descricao}}`, `{{tracos}}`, `{{guardrails}}`, `{{canal}}`, `{{formalidade}}`, `{{emojis}}`, `{{tamanho_max}}` |
| `conversation_summary.md` | Resumo automático no painel do atendente | `{{transcricao}}` |
| `next_best_actions.md` | Sugestões de próxima ação para o atendente | `{{transcricao}}`, `{{contexto_cliente}}` |

## Regras ao editar

- Mantenha as instruções de formato de saída (JSON) intactas: o adaptador faz o parse.
- Os guardrails do Design Studio são injetados em `{{guardrails}}`. Não duplique
  regras aqui — o lugar delas é o Studio, onde a equipe de operação consegue editá-las.
- Se o modelo passar a devolver algo fora do formato, o hub cai automaticamente para
  o classificador por regras. Prompt quebrado degrada a qualidade, não derruba o sistema.
