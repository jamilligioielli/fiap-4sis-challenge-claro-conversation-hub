"""Detecção do humor do cliente, por regras.

Não é análise de sentimento de pesquisa acadêmica — e não precisa ser. O que o
atendente precisa saber ao abrir a conversa é se o cliente chegou calmo ou se
já está na terceira tentativa e perdendo a paciência. Para isso, um léxico em
português, editável sem tocar no código, resolve o caso comum sem depender de
modelo de linguagem, de rede ou de chave — e roda igual no modo degradado.

O resultado é um índice de humor de 0 a 1: 0 é insatisfação forte, 0,5 é
neutro, 1 é satisfação clara. O rótulo sai das faixas abaixo.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from ..value_objects.sentiment import Sentiment

# --------------------------------------------------------------- léxicos
# Expressões compostas são avaliadas antes das palavras soltas e não sofrem
# inversão por negação: "não funciona" já é, inteira, uma reclamação.
NEGATIVE_PHRASES: dict[str, float] = {
    "terceira vez": 0.35, "segunda vez": 0.2, "de novo": 0.2, "outra vez": 0.2,
    "nao funciona": 0.3, "nao resolve": 0.3, "nao resolveu": 0.3, "nao consigo": 0.25,
    "nao aguento": 0.4, "nao estou satisfeito": 0.35, "nao estou satisfeita": 0.35,
    "ninguem resolve": 0.35, "ate agora nada": 0.3, "sem sinal": 0.15,
    "falar com atendente": 0.25, "falar com um atendente": 0.25,
    "falar com uma pessoa": 0.25, "atendente humano": 0.25, "quero falar": 0.15, "cancelar tudo": 0.4, "vou cancelar": 0.35,
    "cobranca indevida": 0.3, "muito caro": 0.2, "perda de tempo": 0.35,
    "ainda estou aguardando": 0.3, "ainda aguardando": 0.3, "ainda estou esperando": 0.3,
    "ainda esperando": 0.3, "ninguem responde": 0.35, "sem resposta": 0.25,
}

NEGATIVE_WORDS: dict[str, float] = {
    "demora": 0.25, "demorando": 0.25, "demorado": 0.25, "lento": 0.2, "lenta": 0.2,
    "lentidao": 0.25, "atrasada": 0.2, "atrasado": 0.2, "atraso": 0.2,
    "ruim": 0.25, "pessimo": 0.4, "pessima": 0.4, "horrivel": 0.4, "absurdo": 0.4,
    "ridiculo": 0.4, "inaceitavel": 0.4, "vergonha": 0.35, "descaso": 0.4,
    "procon": 0.45, "processar": 0.45, "reclamacao": 0.25, "reclamar": 0.2,
    "cancelar": 0.2, "cancelamento": 0.2, "problema": 0.15, "irritado": 0.35,
    "irritada": 0.35, "chateado": 0.3, "chateada": 0.3, "frustrado": 0.35,
    "frustrada": 0.35, "cansado": 0.25, "cansada": 0.25, "caindo": 0.15,
}

POSITIVE_PHRASES: dict[str, float] = {
    "muito obrigado": 0.35, "muito obrigada": 0.35, "deu certo": 0.3,
    "funcionou": 0.3, "resolveu meu problema": 0.4, "gostei muito": 0.35,
    "muito bom": 0.3, "tudo certo": 0.2,
}

POSITIVE_WORDS: dict[str, float] = {
    "obrigado": 0.25, "obrigada": 0.25, "valeu": 0.2, "otimo": 0.3, "otima": 0.3,
    "perfeito": 0.3, "perfeita": 0.3, "excelente": 0.35, "adorei": 0.35, "amei": 0.35,
    "maravilha": 0.3, "resolvido": 0.3, "bom": 0.15, "boa": 0.1, "show": 0.2,
    "top": 0.2, "legal": 0.15, "gostei": 0.3, "gosto": 0.15, "funciona": 0.1, "rapido": 0.15, "satisfeito": 0.3, "satisfeita": 0.3,
}

NEGATORS = ("nao", "nem", "nunca", "jamais")
NEGATION_WINDOW = 2          # palavras antes do termo que podem negá-lo
# Negar um elogio é reclamar ("não gostei"); negar uma reclamação é só um
# elogio fraco ("não é ruim" vale menos que "é bom").
NEGATED_NEGATIVE_FACTOR = 0.6

# Faixas do índice de humor.
NEGATIVE_MAX = 0.4
POSITIVE_MIN = 0.6

# Peso de cada mensagem na leitura da conversa: só as mais recentes contam, e
# cada uma vale mais que a anterior. Um cliente que chegou irritado e foi bem
# atendido não deve continuar marcado como frustrado.
RECENT_MESSAGES = 5


@dataclass(frozen=True)
class SentimentReading:
    sentiment: Sentiment
    score: float


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9\s]", " ", plain)


def _label(score: float) -> Sentiment:
    if score < NEGATIVE_MAX:
        return Sentiment.negative
    if score > POSITIVE_MIN:
        return Sentiment.positive
    return Sentiment.neutral


class SentimentDetectionService:
    def analyze(self, text: str) -> SentimentReading:
        """Humor de uma única mensagem."""
        polarity = self._polarity(text)
        score = max(0.0, min(1.0, 0.5 + polarity / 2))
        return SentimentReading(_label(score), round(score, 3))

    def detect_with_score(self, messages: Sequence[str]) -> SentimentReading:
        """Humor da conversa: média ponderada das mensagens recentes do cliente."""
        recent = [m for m in messages if m and m.strip()][-RECENT_MESSAGES:]
        if not recent:
            return SentimentReading(Sentiment.neutral, 0.5)

        weights = range(1, len(recent) + 1)
        scores = [self.analyze(m).score for m in recent]
        score = sum(s * w for s, w in zip(scores, weights, strict=True)) / sum(weights)
        return SentimentReading(_label(score), round(score, 3))

    def detect(self, messages: Sequence[str]) -> Sentiment:
        return self.detect_with_score(messages).sentiment

    # ------------------------------------------------------------ cálculo
    @staticmethod
    def _polarity(text: str) -> float:
        """Soma dos pesos positivos menos os negativos, limitada a [-1, 1]."""
        normalized = f" {' '.join(_normalize(text).split())} "
        polarity = 0.0

        # 1) expressões compostas — removidas do texto depois de contadas, para
        #    que "muito obrigado" não conte de novo como "obrigado".
        for phrases, sign in ((NEGATIVE_PHRASES, -1), (POSITIVE_PHRASES, 1)):
            for phrase, weight in phrases.items():
                pattern = f" {phrase} "
                hits = normalized.count(pattern)
                if hits:
                    polarity += sign * weight * hits
                    normalized = normalized.replace(pattern, " | ")

        # 2) palavras soltas, com inversão quando negadas ("não gostei",
        #    "não é ruim").
        tokens = normalized.split()
        for index, token in enumerate(tokens):
            if token in NEGATIVE_WORDS:
                weight, sign = NEGATIVE_WORDS[token], -1
            elif token in POSITIVE_WORDS:
                weight, sign = POSITIVE_WORDS[token], 1
            else:
                continue
            window = tokens[max(0, index - NEGATION_WINDOW):index]
            if any(t in NEGATORS for t in window) and "|" not in window:
                if sign < 0:
                    weight *= NEGATED_NEGATIVE_FACTOR
                sign = -sign
            polarity += sign * weight

        # Pontos de exclamação repetidos intensificam o que já foi dito.
        if polarity < 0 and "!!" in text:
            polarity -= 0.1

        return max(-1.0, min(1.0, polarity))
