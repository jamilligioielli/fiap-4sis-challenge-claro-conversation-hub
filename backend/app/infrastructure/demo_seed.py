"""Dados de demonstração das melhorias da Sprint 4 — **opcional**.

O hub continua subindo vazio por padrão: o painel que se move a partir do uso
real é uma escolha de projeto e não muda. Este módulo existe para a gravação do
vídeo e para a arguição, quando é preciso mostrar em poucos minutos o que só
apareceria depois de dezenas de atendimentos:

* conversas encerradas com nota, parte só com o bot e parte com humano, com
  diferença visível de NPS (Melhoria 1);
* conversas transferidas aguardando, com prioridades e esperas diferentes
  (Melhoria 2);
* clientes com várias conversas anteriores (Melhorias 3 e 5);
* mensagens com humor positivo, neutro e negativo (Melhoria 4).

O humor de cada mensagem não é escrito à mão: passa pelo mesmo
`SentimentDetectionService` do atendimento real.

Idempotente: as conversas têm identificadores fixos (`conv_demo_*`) e, se a
primeira já existe, nada é recriado. Liga-se com `DEMO_SEED=true` ou pelo
script `scripts/seed_demo.py`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..domain.entities.conversation import Conversation
from ..domain.entities.handover import Handover
from ..domain.entities.message import Message
from ..domain.entities.nps_survey import NpsSurvey
from ..domain.ports.conversation_repository import ConversationRepository
from ..domain.ports.customer_repository import CustomerRepository
from ..domain.services.nps_service import NpsService
from ..domain.services.sentiment_detection_service import SentimentDetectionService
from ..domain.value_objects.area import Area
from ..domain.value_objects.author import Author
from ..domain.value_objects.channel import Channel
from ..domain.value_objects.clock import utcnow
from ..domain.value_objects.conversation_status import ConversationStatus
from ..domain.value_objects.intent import Intent
from ..domain.value_objects.priority import Priority
from ..domain.value_objects.response_source import ResponseSource

log = logging.getLogger("hub.demo_seed")

DEMO_PREFIX = "conv_demo_"
DEMO_AGENT = "Admin CX"
OTHER_AGENT = "Ana · CX"

C, B, A, S = Author.customer, Author.bot, Author.agent, Author.system

INTENTS: dict[str, Intent] = {
    "segunda_via_fatura": Intent(slug="segunda_via_fatura", name="Segunda Via de Fatura",
                                 confidence=0.95, area=Area.financeiro),
    "alteracao_plano": Intent(slug="alteracao_plano", name="Alteração de Plano",
                              confidence=0.97, area=Area.vendas,
                              entities={"plano": "Claro Flex 50GB"}),
    "suporte_tecnico": Intent(slug="suporte_tecnico", name="Suporte Técnico",
                              confidence=0.86, area=Area.suporte),
    "cancelamento": Intent(slug="cancelamento", name="Cancelamento",
                           confidence=0.93, area=Area.retencao),
    "portabilidade": Intent(slug="portabilidade", name="Portabilidade",
                            confidence=0.91, area=Area.vendas),
    "consulta_informacao": Intent(slug="consulta_informacao", name="Consulta de Informação",
                                  confidence=0.74, area=Area.vendas),
    "cobranca": Intent(slug="segunda_via_fatura", name="Contestação de Cobrança",
                       confidence=0.68, area=Area.financeiro),
}

# ------------------------------------------------------------- roteiros
# Cada roteiro é a transcrição sem a pesquisa de NPS, que é acrescentada pelo
# montador conforme a nota de cada instância.
SCRIPTS: dict[str, dict] = {
    "fatura": {
        "intent": "segunda_via_fatura", "human": False,
        "lines": [
            (C, "Oi, preciso da segunda via da minha fatura"),
            (B, "Claro! Sua fatura de R$ 79,90 vence no dia 10. Acabei de enviar a segunda "
                "via para o seu e-mail cadastrado."),
            (C, "Perfeito, chegou aqui. Obrigada!"),
        ],
    },
    "plano": {
        "intent": "alteracao_plano", "human": False,
        "lines": [
            (C, "Quero aumentar minha franquia, está acabando todo mês"),
            (B, "Vi que você usa 85% da franquia. O Claro Flex 50GB sai por R$ 109,90 e já "
                "vale no próximo ciclo. Quer que eu faça a troca?"),
            (C, "Pode ser o de 50GB"),
            (B, "Pronto! A troca para o Claro Flex 50GB foi registrada e passa a valer no "
                "próximo ciclo."),
            (C, "Ótimo, valeu"),
        ],
    },
    "suporte_bot": {
        "intent": "suporte_tecnico", "human": False,
        "lines": [
            (C, "Minha internet está lenta desde ontem"),
            (B, "Rodei um diagnóstico na sua linha: o sinal está normal, mas o roteador está "
                "sem atualização. Pode reiniciá-lo pelo botão de trás?"),
            (C, "Reiniciei e voltou ao normal, obrigado"),
        ],
    },
    "suporte_humano": {
        "intent": "suporte_tecnico", "human": True,
        "reason": "Cliente solicitou falar com atendente",
        "lines": [
            (C, "Já é a terceira vez que a internet cai essa semana"),
            (B, "Sinto muito pelo transtorno. O diagnóstico mostra oscilação na sua região. "
                "Quer que eu abra um chamado técnico?"),
            (C, "Quero falar com um atendente, por favor"),
            (S, "Conversa transferida para atendimento humano — Cliente solicitou falar com "
                "atendente"),
            (A, "Oi! Aqui é do atendimento técnico. Já estou com todo o histórico, não precisa "
                "repetir nada."),
            (A, "Agendei uma visita técnica para amanhã de manhã e deixei um crédito de 5GB "
                "na sua linha pelo transtorno."),
            (C, "Muito obrigado pela atenção, resolveu meu problema"),
        ],
    },
    "retencao": {
        "intent": "cancelamento", "human": True,
        "reason": "Pedido de cancelamento encaminhado à retenção",
        "lines": [
            (C, "Quero cancelar meu plano, está muito caro"),
            (B, "Entendo. Antes de seguir, posso entender o que mais está pesando?"),
            (C, "O preço mesmo, e o sinal às vezes cai"),
            (S, "Conversa transferida para atendimento humano — Pedido de cancelamento "
                "encaminhado à retenção"),
            (A, "Olá! Vi que você é cliente há bastante tempo. Consigo manter o seu plano com "
                "20% de desconto por 12 meses e verificar o sinal da sua região."),
            (C, "Gostei da proposta, vou ficar"),
        ],
    },
    "portabilidade": {
        "intent": "portabilidade", "human": False,
        "lines": [
            (C, "Quero trazer meu número da outra operadora"),
            (B, "Dá sim! A portabilidade leva até 3 dias úteis e o seu número continua "
                "funcionando durante o processo. Já posso iniciar?"),
            (C, "Entendi, pode iniciar. Obrigado"),
        ],
    },
    "consulta": {
        "intent": "consulta_informacao", "human": False,
        "lines": [
            (C, "Quais planos família vocês têm?"),
            (B, "Temos o Claro Família 4 linhas por R$ 249,90 com 200GB compartilhados, e o "
                "de 3 linhas por R$ 199,90."),
            (C, "Legal, vou pensar e volto depois"),
        ],
    },
    "cobranca": {
        "intent": "cobranca", "human": True,
        "reason": "Insatisfação detectada na mensagem do cliente",
        "lines": [
            (C, "Veio uma cobrança indevida na minha fatura, isso é um absurdo"),
            (S, "Conversa transferida para atendimento humano — Insatisfação detectada na "
                "mensagem do cliente"),
            (A, "Peço desculpas pelo erro. Já identifiquei a cobrança e o estorno sai na "
                "próxima fatura."),
            (C, "Ok, mas demorou bastante para alguém responder"),
        ],
    },
    "fatura_demora": {
        "intent": "segunda_via_fatura", "human": False,
        "lines": [
            (C, "Preciso da fatura, o app não abre de novo"),
            (B, "Enviei a segunda via por aqui mesmo. O aplicativo passou por instabilidade "
                "hoje cedo e já está normalizado."),
            (C, "Ok"),
        ],
    },
}


@dataclass
class Closed:
    """Uma conversa encerrada da demonstração."""
    key: str
    customer: str
    script: str
    days_ago: float
    channel: Channel
    score: int | None = None
    dismissed: bool = False
    agent: str = OTHER_AGENT


@dataclass
class Waiting:
    """Uma conversa transferida, ainda aguardando atendimento humano."""
    key: str
    customer: str
    intent: str
    channel: Channel
    minutes_waiting: int
    priority: Priority
    reason: str
    lines: list[tuple[Author, str]] = field(default_factory=list)
    agent: str | None = None


CLOSED: list[Closed] = [
    # Maria — seis atendimentos: a linha do tempo completa.
    Closed("m1", "cust_maria_silva", "fatura", 150, Channel.app, score=9),
    Closed("m2", "cust_maria_silva", "suporte_bot", 96, Channel.whatsapp, score=6),
    Closed("m3", "cust_maria_silva", "suporte_humano", 61, Channel.whatsapp, score=10),
    Closed("m4", "cust_maria_silva", "consulta", 33, Channel.web, score=8),
    Closed("m5", "cust_maria_silva", "fatura_demora", 12, Channel.app, dismissed=True),
    Closed("m6", "cust_maria_silva", "plano", 4.2, Channel.whatsapp, score=9),
    # Carla — histórico de suporte técnico.
    Closed("c1", "cust_carla_mendes", "suporte_bot", 75, Channel.whatsapp, score=4),
    Closed("c2", "cust_carla_mendes", "suporte_humano", 40, Channel.whatsapp, score=9),
    Closed("c3", "cust_carla_mendes", "suporte_bot", 9, Channel.web, score=5),
    # Felipe — atrito com cobrança.
    Closed("f1", "cust_felipe_barros", "cobranca", 26, Channel.whatsapp, score=7),
    Closed("f2", "cust_felipe_barros", "retencao", 5.3, Channel.whatsapp, score=9),
    # Juliana, João e Ricardo.
    Closed("j1", "cust_juliana_rocha", "fatura", 30, Channel.app, score=10),
    Closed("j2", "cust_juliana_rocha", "fatura", 1.4, Channel.app, score=8),
    Closed("o1", "cust_joao_santos", "portabilidade", 3.1, Channel.whatsapp, score=8),
    Closed("o2", "cust_joao_santos", "consulta", 2.2, Channel.whatsapp, dismissed=True),
    Closed("r1", "cust_ricardo_lima", "consulta", 6.0, Channel.web, score=7),
    Closed("r2", "cust_ricardo_lima", "plano", 0.9, Channel.web, score=6),
    Closed("r3", "cust_ricardo_lima", "suporte_humano", 0.5, Channel.web, score=10,
           agent=DEMO_AGENT),
]

WAITING: list[Waiting] = [
    Waiting("w1", "cust_felipe_barros", "cancelamento", Channel.whatsapp, 42, Priority.high,
            "Pedido de cancelamento encaminhado à retenção", [
                (C, "Quero cancelar tudo, o atendimento de vocês é péssimo"),
                (B, "Sinto muito por isso. Vou te passar para alguém da nossa equipe de "
                    "retenção, com todo o histórico."),
                (S, "Conversa transferida para atendimento humano — Pedido de cancelamento "
                    "encaminhado à retenção"),
                (C, "Que demora, ninguém responde? É um absurdo"),
            ]),
    Waiting("w2", "cust_carla_mendes", "suporte_tecnico", Channel.whatsapp, 18, Priority.high,
            "Cliente solicitou falar com atendente", [
                (C, "A internet caiu de novo, já é a terceira vez esse mês"),
                (B, "Rodei o diagnóstico e há oscilação na sua região. Posso abrir um "
                    "chamado técnico?"),
                (C, "Quero falar com atendente"),
                (S, "Conversa transferida para atendimento humano — Cliente solicitou falar "
                    "com atendente"),
                (C, "Ainda estou aguardando"),
            ]),
    Waiting("w3", "cust_juliana_rocha", "segunda_via_fatura", Channel.app, 25, Priority.medium,
            "Baixa confiança na classificação após 2 tentativas", [
                (C, "Minha fatura veio com um valor diferente do mês passado"),
                (B, "Posso te enviar a segunda via com o detalhamento. Quer que eu envie?"),
                (C, "Não é isso, quero entender a diferença"),
                (S, "Conversa transferida para atendimento humano — Baixa confiança na "
                    "classificação após 2 tentativas"),
                (A, "Oi, Juliana! Estou conferindo o detalhamento da sua fatura e já te "
                    "explico."),
            ], agent=DEMO_AGENT),
    Waiting("w4", "cust_joao_santos", "portabilidade", Channel.whatsapp, 7, Priority.medium,
            "Cliente solicitou falar com atendente", [
                (C, "Tenho uma dúvida sobre o contrato da portabilidade"),
                (B, "Posso ajudar com prazos e documentos. O que você gostaria de saber?"),
                (C, "Prefiro tratar com uma pessoa, pode me passar para alguém?"),
                (S, "Conversa transferida para atendimento humano — Cliente solicitou falar "
                    "com atendente"),
            ]),
    Waiting("w5", "cust_ricardo_lima", "alteracao_plano", Channel.web, 3, Priority.low,
            "Venda consultiva encaminhada a especialista", [
                (C, "Quero contratar o plano família para 4 linhas"),
                (B, "Ótima escolha! Vou te passar para um especialista que monta a melhor "
                    "combinação para a sua família."),
                (S, "Conversa transferida para atendimento humano — Venda consultiva "
                    "encaminhada a especialista"),
                (C, "Perfeito, obrigado, aguardo"),
            ]),
]


# ------------------------------------------------------------- montagem
class _Builder:
    def __init__(self, names: dict[str, str], now: datetime) -> None:
        self._names = names
        self._now = now
        self._sentiment = SentimentDetectionService()

    def _messages(self, conversation_id: str, lines: list[tuple[Author, str]],
                  start: datetime, channel: Channel) -> list[Message]:
        messages = []
        for index, (author, text) in enumerate(lines):
            messages.append(Message(
                conversation_id=conversation_id, author=author, text=text,
                channel=None if author is Author.system else channel,
                timestamp=start + timedelta(minutes=index * 2),
                source=ResponseSource.template if author is Author.bot else None,
                sentiment=(self._sentiment.analyze(text).sentiment
                           if author is Author.customer else None),
            ))
        return messages

    def _apply_sentiment(self, conversation: Conversation, messages: list[Message]) -> None:
        texts = [m.text for m in messages if m.author is Author.customer]
        reading = self._sentiment.detect_with_score(texts)
        conversation.update_sentiment(reading.sentiment, reading.score)

    def closed(self, spec: Closed) -> tuple[Conversation, list[Message]]:
        script = SCRIPTS[spec.script]
        intent = INTENTS[script["intent"]]
        conversation_id = f"{DEMO_PREFIX}{spec.key}"
        start = self._now - timedelta(days=spec.days_ago)

        first_name = self._names.get(spec.customer, "").split(" ")[0]
        lines = list(script["lines"])
        lines.append((B, NpsService.question(first_name)))
        if spec.score is not None:
            lines.append((C, str(spec.score)))
            lines.append((B, NpsService.acknowledgement(spec.score, first_name)))
        elif spec.dismissed:
            lines.append((C, "prefiro não responder"))
            lines.append((B, NpsService.farewell()))

        messages = self._messages(conversation_id, lines, start, spec.channel)
        human = bool(script["human"])
        closed_at = messages[-1].timestamp
        closed_by = spec.agent if human else "bot"

        survey = NpsSurvey(sent_at=closed_at - timedelta(minutes=2), closed_by=closed_by,
                           dismissed=spec.dismissed)
        if spec.score is not None:
            survey.record(spec.score)
            survey.answered_at = closed_at

        conversation = Conversation(
            id=conversation_id, session_id=f"ses_demo_{spec.key}",
            customer_id=spec.customer, customer_name=self._names.get(spec.customer, ""),
            status=ConversationStatus.pending, area=intent.area,
            priority=Priority.high if human else Priority.medium,
            channels_used=[spec.channel], started_at=start, updated_at=closed_at,
            last_message=messages[-1].text, unread=False, intent=intent,
            nps=survey, closed_at=closed_at,
            agent_replies=sum(1 for m in messages if m.author is Author.agent),
        )
        if human:
            transfer = next(m for m in messages if m.author is Author.system)
            conversation.handover = Handover(
                requested=True, reason=script["reason"], requested_at=transfer.timestamp,
                assigned_agent=spec.agent, services_consulted=["crm", "diagnostico_rede"],
                transcript_size=messages.index(transfer),
            )
        self._apply_sentiment(conversation, messages)
        return conversation, messages

    def waiting(self, spec: Waiting) -> tuple[Conversation, list[Message]]:
        intent = INTENTS[spec.intent]
        conversation_id = f"{DEMO_PREFIX}{spec.key}"
        transfer_index = next(i for i, (a, _) in enumerate(spec.lines) if a is Author.system)
        # A transferência aconteceu há `minutes_waiting`; as falas anteriores vêm antes.
        transferred_at = self._now - timedelta(minutes=spec.minutes_waiting)
        start = transferred_at - timedelta(minutes=transfer_index * 2)
        messages = self._messages(conversation_id, spec.lines, start, spec.channel)
        # Ninguém escreve no futuro: as falas depois da transferência ficam
        # espalhadas entre a transferência e agora.
        after = messages[transfer_index + 1:]
        for offset, message in enumerate(after, start=1):
            message.timestamp = transferred_at + (self._now - transferred_at) * (
                offset / (len(after) + 1))

        # Aviso de sistema não é "última mensagem" de ninguém — no atendimento
        # real ele também não entra nesse campo.
        last = next(m for m in reversed(messages) if m.author is not Author.system)
        conversation = Conversation(
            id=conversation_id, session_id=f"ses_demo_{spec.key}",
            customer_id=spec.customer, customer_name=self._names.get(spec.customer, ""),
            status=ConversationStatus.transferred, area=intent.area, priority=spec.priority,
            channels_used=[spec.channel], started_at=start, updated_at=last.timestamp,
            last_message=last.text, unread=last.author is Author.customer, intent=intent,
            agent_replies=sum(1 for m in messages if m.author is Author.agent),
            handover=Handover(
                requested=True, reason=spec.reason, requested_at=transferred_at,
                assigned_agent=spec.agent, services_consulted=["crm"],
                transcript_size=transfer_index,
            ),
        )
        self._apply_sentiment(conversation, messages)
        return conversation, messages


async def populate_demo(customers: CustomerRepository,
                        conversations: ConversationRepository,
                        now: datetime | None = None) -> int:
    """Grava as conversas de demonstração. Devolve quantas foram criadas (0 se já havia)."""
    first_id = f"{DEMO_PREFIX}{CLOSED[0].key}"
    if await conversations.get(first_id) is not None:
        log.info("Dados de demonstração já presentes — nada a fazer.")
        return 0

    names = {c.id: c.name for c in await customers.all()}
    builder = _Builder(names, now or utcnow())
    created = 0
    for conversation, messages in ([builder.closed(s) for s in CLOSED]
                                   + [builder.waiting(s) for s in WAITING]):
        if conversation.customer_id not in names:
            continue
        for message in messages:
            await conversations.add_message(message)
        await conversations.save(conversation)
        created += 1

    log.info("Dados de demonstração criados: %d conversas.", created)
    return created
