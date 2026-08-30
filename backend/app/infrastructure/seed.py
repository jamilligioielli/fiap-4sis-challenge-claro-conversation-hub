"""Dados iniciais.

Reproduzem exatamente a historia que a interface do protótipo ja conta: a Maria
Silva pedindo alteracao de plano, comecando no Web Chat e migrando para o
WhatsApp. Back-end, front-end e o video de demonstracao contam a mesma coisa.
"""
from __future__ import annotations

from datetime import timedelta

from ..domain.entities import Conversation, Customer, Message, Plan, TimelineEvent
from ..domain.studio import (ChannelConfig, ChannelPresentation, ConfiguredIntent,
                             Guardrail, Persona, StudioConfig, VoiceConfig)
from ..domain.value_objects import (Area, Author, Channel, ConversationStatus,
                                    Intent, IntentEngine, Priority, utcnow)

# --------------------------------------------------------------- Design Studio
VOICE_DEFAULTS = VoiceConfig(
    speechRate=50, voiceGender="feminino", vocabularyLevel=40,
    captureMode="hybrid", menuPattern="option-key", maxMenuOptions=5,
    autoRepeatTimeout=8, maxAttempts=3, silenceTimeout=3000,
    transferTriggers=[
        "Cliente solicita falar com atendente",
        "Falha de reconhecimento após 3 tentativas",
        "Intent de insatisfação detectada",
        "Assunto fora do escopo da URA",
    ],
    queueMessage=("Por favor, aguarde. Você será atendido em instantes. "
                  "Sua ligação é muito importante para nós."),
    scriptOpening=("Olá, {nome}! Você ligou para a Claro. Sou a Clara, sua assistente "
                   "virtual. Para continuar, precisarei verificar sua identidade."),
    scriptMenu=("Você pode dizer o que precisa ou pressionar uma das opções. Para alteração "
                "de plano, pressione 1. Para segunda via de fatura, pressione 2. Para suporte "
                "técnico, pressione 3. Para falar com um atendente, pressione 0."),
    scriptFarewell=("Obrigada por entrar em contato com a Claro, {nome}. Seu atendimento foi "
                    "encerrado. Tenha um ótimo dia!"),
    pronunciationGlossary=[
        {"term": "Claro", "pronunciation": "Claro"},
        {"term": "PIX", "pronunciation": "Pix"},
        {"term": "CPF", "pronunciation": "C, P, F"},
        {"term": "URA", "pronunciation": "U, R, A"},
        {"term": "Wi-Fi", "pronunciation": "Uai-Fai"},
        {"term": "SMS", "pronunciation": "S, M, S"},
    ],
)

DEFAULT_STUDIO = StudioConfig(
    persona=Persona(
        name="Clara",
        description=("Clara é uma assistente virtual da Claro que ajuda clientes com simpatia, "
                     "eficiência e profissionalismo. Ela é proativa, empática e busca resolver "
                     "problemas de forma rápida, sempre mantendo o cliente informado sobre cada "
                     "etapa do atendimento."),
        traits=["Empática", "Eficiente", "Proativa", "Profissional", "Amigável"],
    ),
    intents=[
        ConfiguredIntent(slug="alteracao_plano", name="Alteração de Plano", confidence="Alta",
                         examples="quero mudar de plano, alterar meu plano"),
        ConfiguredIntent(slug="segunda_via_fatura", name="Segunda Via de Fatura",
                         confidence="Alta", examples="segunda via, minha fatura, conta atrasada"),
        ConfiguredIntent(slug="suporte_tecnico", name="Suporte Técnico", confidence="Média",
                         examples="internet lenta, sem sinal, não conecta"),
        ConfiguredIntent(slug="portabilidade", name="Portabilidade", confidence="Alta",
                         examples="portar número, trazer número, mudar operadora"),
        ConfiguredIntent(slug="cancelamento", name="Cancelamento", confidence="Alta",
                         examples="cancelar plano, desistir, encerrar contrato"),
        ConfiguredIntent(slug="falar_atendente", name="Falar com Atendente", confidence="Alta",
                         examples="quero falar com atendente, me passa para uma pessoa"),
        ConfiguredIntent(slug="consulta_informacao", name="Consulta de Informação",
                         confidence="Média", examples="quanto custa, quais planos, promoção"),
    ],
    guardrails=[
        Guardrail(rule="Nunca compartilhar dados pessoais sem validação", category="Segurança"),
        Guardrail(rule="Não realizar alterações contratuais sem confirmação explícita",
                  category="Compliance"),
        Guardrail(rule="Transferir para humano em casos de insatisfação detectada",
                  category="Experiência"),
        Guardrail(rule="Manter tom respeitoso mesmo diante de agressividade", category="Marca"),
        Guardrail(rule="Não fazer promessas que não possam ser cumpridas", category="Ética"),
    ],
    channels=[
        ChannelConfig(
            id="whatsapp", name="WhatsApp", formalityLevel=30, greeting="Oi, {nome}! 👋",
            maxLength=160, useEmoji=True,
            guidelines=["Use linguagem informal e amigável",
                        "Incluir emojis relevantes com moderação",
                        "Mensagens curtas e diretas",
                        "Botões de resposta rápida quando possível"],
            sampleMessage="Oi, Maria! 👋 Vi que você quer alterar seu plano. Posso te ajudar com isso!",
            presentation=ChannelPresentation(color="text-green-600", bgColor="bg-green-50",
                                             iconColor="bg-green-50"),
        ),
        ChannelConfig(
            id="webchat", name="Web Chat", formalityLevel=55, greeting="Olá, {nome}!",
            maxLength=280, useEmoji=False,
            guidelines=["Tom profissional e estruturado",
                        "Sem emojis, usar formatação de texto",
                        "Links clicáveis quando necessário",
                        "Mensagens detalhadas são aceitáveis"],
            sampleMessage=("Olá, Maria! Vejo que você gostaria de alterar seu plano. "
                           "Ficarei feliz em auxiliar você neste processo."),
            presentation=ChannelPresentation(color="text-blue-600", bgColor="bg-blue-50",
                                             iconColor="bg-blue-50"),
        ),
        ChannelConfig(
            id="app", name="App Claro", formalityLevel=45, greeting="Olá, {nome}",
            maxLength=200, useEmoji=False,
            guidelines=["Tom moderno e direto",
                        "Aproveitar componentes nativos do app",
                        "Integrar ações contextuais do app",
                        "Notificações push para acompanhamento"],
            sampleMessage="Olá, Maria. Quer alterar seu plano? Veja as opções disponíveis para você aqui.",
            presentation=ChannelPresentation(color="text-red-600", bgColor="bg-red-50",
                                             iconColor="bg-red-50"),
        ),
        ChannelConfig(
            id="voice", name="Voz (URA)", formalityLevel=50, greeting="", maxLength=120,
            useEmoji=False, guidelines=[], sampleMessage="",
            presentation=ChannelPresentation(color="text-purple-600", bgColor="bg-purple-50",
                                             iconColor="bg-purple-50"),
            voiceConfig=VOICE_DEFAULTS,
        ),
    ],
)

# --------------------------------------------------------------------- cliente
MARIA = Customer(
    id="cust_maria_silva",
    name="Maria Silva Santos",
    document_masked="***.***.***-42",
    birth_date="15/03/1985",
    customer_since="Janeiro 2023",
    segment="VIP",
    email="maria.silva@email.com",
    phone="(11) 98765-4321",
    preferred_channel=Channel.whatsapp,
    plan=Plan(name="Claro Flex 30GB", price=79.90, data_gb=30, used_gb=25.5,
              line="(11) 98765-4321", due_day=10, status="Ativo"),
    products=[
        {"name": "Claro Flex 30GB", "status": "Ativo", "description": "Linha móvel • (11) 98765-4321"},
        {"name": "Claro TV+ 100 canais", "status": "Ativo", "description": "TV por assinatura"},
        {"name": "Claro Internet 500MB", "status": "Ativo", "description": "Internet residencial"},
    ],
    timeline=[
        TimelineEvent(date="18/05/2026 14:32",
                      event="Iniciou conversa no Web Chat sobre alteração de plano",
                      type="conversation"),
        TimelineEvent(date="18/05/2026 14:33",
                      event="Migrou para WhatsApp mantendo contexto", type="channel"),
        TimelineEvent(date="15/05/2026 09:15",
                      event="Consultou segunda via de fatura no App", type="app"),
        TimelineEvent(date="10/05/2026 16:45",
                      event="Atendimento técnico - problema de sinal resolvido", type="support"),
        TimelineEvent(date="28/04/2026 11:20", event="Pagamento de fatura em dia", type="payment"),
        TimelineEvent(date="15/04/2026 14:00", event="Upgrade de plano 20GB → 30GB", type="plan"),
    ],
    churn_risk=0.12,
    churn_factors=[
        {"text": "Pagamentos pontuais", "positive": True},
        {"text": "Alta utilização de serviços", "positive": True},
        {"text": "Engajamento recente", "positive": True},
    ],
    aliases={"whatsapp": "5511987654321", "web": "sess-web-maria", "app": "device-maria-01"},
)

OTHER_CUSTOMERS = [
    ("cust_joao_santos", "João Santos", Channel.whatsapp),
    ("cust_ana_costa", "Ana Costa", Channel.app),
    ("cust_pedro_oliveira", "Pedro Oliveira", Channel.voice),
    ("cust_carla_mendes", "Carla Mendes", Channel.whatsapp),
    ("cust_ricardo_lima", "Ricardo Lima", Channel.web),
    ("cust_juliana_rocha", "Juliana Rocha", Channel.app),
    ("cust_felipe_barros", "Felipe Barros", Channel.whatsapp),
    ("cust_camila_torres", "Camila Torres", Channel.web),
    ("cust_bruno_alves", "Bruno Alves", Channel.voice),
    ("cust_larissa_nunes", "Larissa Nunes", Channel.app),
    ("cust_marcos_ferreira", "Marcos Ferreira", Channel.whatsapp),
    ("cust_patricia_gomes", "Patrícia Gomes", Channel.web),
    ("cust_diego_cardoso", "Diego Cardoso", Channel.voice),
]

# (customer_id, canal, status, ultima mensagem, minutos atras, prioridade, area, nao lida)
CONVERSATION_SEED = [
    ("cust_joao_santos", Channel.whatsapp, ConversationStatus.waiting,
     "Ok, aguardo retorno sobre a portabilidade", 5, Priority.medium, Area.suporte, False),
    ("cust_ana_costa", Channel.app, ConversationStatus.transferred,
     "Transferido para especialista técnico", 12, Priority.high, Area.tecnico, False),
    ("cust_pedro_oliveira", Channel.voice, ConversationStatus.pending,
     "Callback agendado para 14:30", 18, Priority.low, Area.retencao, False),
    ("cust_carla_mendes", Channel.whatsapp, ConversationStatus.active,
     "Minha internet está muito lenta hoje", 25, Priority.medium, Area.suporte, True),
    ("cust_ricardo_lima", Channel.web, ConversationStatus.waiting,
     "Gostaria de saber sobre os planos família", 32, Priority.low, Area.vendas, False),
    ("cust_juliana_rocha", Channel.app, ConversationStatus.active,
     "Não consigo acessar minha segunda via de fatura", 45, Priority.medium, Area.financeiro, False),
    ("cust_felipe_barros", Channel.whatsapp, ConversationStatus.active,
     "Quero cancelar meu plano, não estou satisfeito", 52, Priority.high, Area.retencao, True),
    ("cust_camila_torres", Channel.web, ConversationStatus.waiting,
     "Recebi um SMS de promoção e quero saber mais", 60, Priority.low, Area.marketing, False),
    ("cust_bruno_alves", Channel.voice, ConversationStatus.pending,
     "Solicito negociação do débito em aberto", 70, Priority.high, Area.financeiro, False),
    ("cust_larissa_nunes", Channel.app, ConversationStatus.active,
     "O roteador parou de funcionar após a atualização", 80, Priority.medium, Area.tecnico, False),
    ("cust_marcos_ferreira", Channel.whatsapp, ConversationStatus.transferred,
     "Quero fazer upgrade para o plano corporativo", 95, Priority.medium, Area.vendas, False),
    ("cust_patricia_gomes", Channel.web, ConversationStatus.active,
     "Participei da campanha e não recebi o bônus", 110, Priority.medium, Area.marketing, True),
    ("cust_diego_cardoso", Channel.voice, ConversationStatus.waiting,
     "Internet caiu há 3 horas, preciso de ajuda urgente", 120, Priority.high, Area.suporte, False),
]

# A jornada da Maria: comeca no Web Chat, migra para o WhatsApp sem perder contexto.
MARIA_JOURNEY = [
    (Author.customer, "Olá, gostaria de alterar meu plano", Channel.web),
    (Author.bot, ("Olá, Maria! Vejo que você gostaria de alterar seu plano. Ficarei feliz em "
                  "auxiliar você neste processo. Você já sabe qual plano gostaria de contratar?"),
     Channel.web),
    (Author.customer, "Quero o Claro Flex 50GB", Channel.web),
    (Author.system, "Cliente migrou de Web Chat para WhatsApp mantendo histórico completo", None),
    (Author.customer, "Estou pelo celular agora", Channel.whatsapp),
    (Author.bot, ("Perfeito, Maria! Continuamos sua solicitação aqui no WhatsApp. O plano Claro "
                  "Flex 50GB custa R$ 99,90/mês. Posso prosseguir com a alteração?"),
     Channel.whatsapp),
    (Author.customer, "Sim, pode prosseguir", Channel.whatsapp),
]

MARIA_INTENT = Intent(
    slug="alteracao_plano", name="Alteração de Plano", confidence=0.98,
    area=Area.vendas, entities={"plano": "Claro Flex 50GB"}, engine=IntentEngine.rules,
    reasoning="Cliente declarou explicitamente o plano desejado.",
)


async def populate(customers, conversations, studio) -> None:
    """Idempotente: se a Maria ja existe, o seed nao roda de novo."""
    if await customers.get(MARIA.id):
        return

    await studio.save(DEFAULT_STUDIO)
    await customers.save(MARIA)

    now = utcnow()

    # -- conversa principal (Maria) ---------------------------------------
    conv = Conversation(
        id="conv_maria_alteracao_plano",
        session_id="ses_maria_demo",
        customer_id=MARIA.id,
        customer_name=MARIA.name,
        status=ConversationStatus.active,
        area=Area.vendas,
        priority=Priority.high,
        channels_used=[Channel.web, Channel.whatsapp],
        started_at=now - timedelta(minutes=3),
        updated_at=now - timedelta(minutes=2),
        last_message="Preciso alterar meu plano para o Claro Flex 50GB",
        unread=True,
        intent=MARIA_INTENT,
    )
    await conversations.save(conv)

    for offset, (author, text, channel) in enumerate(MARIA_JOURNEY):
        await conversations.add_message(Message(
            conversation_id=conv.id, author=author, text=text, channel=channel,
            timestamp=now - timedelta(minutes=3) + timedelta(seconds=offset * 25),
            intent=MARIA_INTENT if author is Author.customer and offset == 0 else None,
        ))

    # -- demais conversas da fila do Inbox --------------------------------
    for cid, name, channel in OTHER_CUSTOMERS:
        await customers.save(Customer(id=cid, name=name, preferred_channel=channel))

    for cid, channel, status, text, minutes, priority, area, unread in CONVERSATION_SEED:
        name = next(n for c, n, _ in OTHER_CUSTOMERS if c == cid)
        started = now - timedelta(minutes=minutes)
        other = Conversation(
            session_id=f"ses_{cid}", customer_id=cid, customer_name=name,
            status=status, area=area, priority=priority, channels_used=[channel],
            started_at=started, updated_at=started, last_message=text, unread=unread,
        )
        await conversations.save(other)
        await conversations.add_message(Message(
            conversation_id=other.id, author=Author.customer, text=text,
            channel=channel, timestamp=started,
        ))
