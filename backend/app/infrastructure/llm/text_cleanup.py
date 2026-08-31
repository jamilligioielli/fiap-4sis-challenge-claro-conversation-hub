"""Higienização do texto devolvido pelo modelo.

Modelos gostam de embrulhar a resposta em aspas, prefixar com o nome do
personagem ou devolver markdown. Nada disso deve chegar ao cliente.
"""
from __future__ import annotations

import re

PREFIXES = re.compile(
    r"^\s*(clara|assistente|resposta|mensagem|bot)\s*[:\-–]\s*", re.IGNORECASE)
FENCE = re.compile(r"^```[a-z]*\n?|\n?```$", re.IGNORECASE)

# Modelos de raciocínio (gpt-oss, qwen, deepseek-r1) devolvem o raciocínio antes
# da resposta. O certo é desligá-lo no pedido — `LLM_EXTRA_PARAMS` faz isso —,
# mas o parâmetro depende do provedor e já houve caso de vazar mesmo desligado.
# Aqui é rede de segurança: entre "o cliente lê o raciocínio do robô" e "uma
# regex a mais", a escolha é fácil.
THINK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.IGNORECASE | re.DOTALL)
OPEN_THINK = re.compile(r"<(think|thinking|reasoning)>.*$", re.IGNORECASE | re.DOTALL)
# O formato harmony do gpt-oss separa o raciocínio da resposta em canais:
#   <|start|>assistant<|channel|>analysis<|message|>… pensando …<|end|>
#   <|start|>assistant<|channel|>final<|message|>… a resposta …<|return|>
# Só o canal `final` interessa ao cliente. Cortar por marcador em vez de apagar
# os marcadores preserva a resposta em vez de colar os canais um no outro.
HARMONY_FINAL = re.compile(r"<\|channel\|>\s*final\s*<\|message\|>", re.IGNORECASE)
HARMONY_TOKENS = re.compile(r"<\|[a-z_]+\|>", re.IGNORECASE)


def clean_reply(text: str) -> str:
    text = (text or "").strip()

    # Bloco de raciocínio fechado sai inteiro. Um bloco que abriu e não fechou
    # significa que o limite de tokens cortou o raciocínio no meio: aí não
    # sobrou resposta nenhuma, e devolver vazio faz o redator de reserva
    # assumir — melhor do que entregar meio pensamento ao cliente.
    text = THINK.sub("", text).strip()
    text = OPEN_THINK.sub("", text).strip()

    if (marker := list(HARMONY_FINAL.finditer(text))):
        text = text[marker[-1].end():]
    text = HARMONY_TOKENS.sub("", text).strip()

    text = FENCE.sub("", text).strip()
    text = PREFIXES.sub("", text).strip()

    # aspas envolvendo a mensagem inteira
    for opening, closing in (('"', '"'), ("“", "”"), ("'", "'")):
        if text.startswith(opening) and text.endswith(closing) and len(text) > 2:
            text = text[1:-1].strip()

    # Modelos costumam devolver `"Clara: ..."` — com o prefixo *dentro* das
    # aspas. Só depois de desembrulhar dá para vê-lo.
    text = PREFIXES.sub("", text).strip()

    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()
