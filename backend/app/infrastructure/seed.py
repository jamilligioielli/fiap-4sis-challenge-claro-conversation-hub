"""Dados iniciais: apenas o cadastro de clientes.

**Nenhuma conversa é semeada.** O painel operacional começa vazio de propósito —
os números vêm do uso, e mandar uma mensagem pelo simulador é o que faz o
indicador se mover na tela. Um dashboard cheio antes do primeiro atendimento é
uma tela bonita que não prova nada.

Os clientes existem porque são as personas com quem se simula, e cada um carrega
um resumo de comportamento que entra no contexto do assistente.
"""
from __future__ import annotations

from datetime import timedelta

from ..domain.entities.customer import Customer
from ..domain.entities.plan import Plan
from ..domain.entities.timeline_event import TimelineEvent
from ..domain.studio.channel_config import ChannelConfig
from ..domain.studio.channel_presentation import ChannelPresentation
from ..domain.studio.configured_intent import ConfiguredIntent
from ..domain.studio.guardrail import Guardrail
from ..domain.studio.persona import Persona
from ..domain.studio.studio_config import StudioConfig
from ..domain.studio.voice_config import VoiceConfig
from ..domain.value_objects.channel import Channel
from ..domain.value_objects.clock import utcnow

# ------------------------------------------------------------- Design Studio
VOICE_DEFAULTS = VoiceConfig(
    speechRate=50, voiceGender="feminino", vocabularyLevel=40,
    captureMode="hybrid", menuPattern="option-key", maxMenuOptions=5,
    autoRepeatTimeout=8, maxAttempts=3, silenceTimeout=3000,
    transferTriggers=[
        "Cliente solicita falar com atendente",
        "Falha de reconhecimento após 3 tentativas",
        "Insatisfação detectada",
        "Assunto fora do escopo da URA",
    ],
    queueMessage=("Por favor, aguarde. Você será atendido em instantes. "
                  "Sua ligação é muito importante para nós."),
    scriptOpening=("Olá, {nome}! Você ligou para a Claro. Sou a Clara, sua assistente "
                   "virtual. Para continuar, precisarei verificar sua identidade."),
    scriptMenu=("Você pode dizer o que precisa ou pressionar uma das opções. Para alteração "
                "de plano, pressione 1. Para segunda via de fatura, pressione 2. Para "
                "suporte técnico, pressione 3. Para falar com um atendente, pressione 0."),
    scriptFarewell=("Obrigada por entrar em contato com a Claro, {nome}. Seu atendimento "
                    "foi encerrado. Tenha um ótimo dia!"),
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
        description=("Clara é uma assistente virtual da Claro que ajuda clientes com "
                     "simpatia, eficiência e profissionalismo. É proativa, empática e busca "
                     "resolver problemas de forma rápida, sempre mantendo o cliente "
                     "informado sobre cada etapa do atendimento."),
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
        Guardrail(rule="Não citar valor, prazo ou condição que não venha dos sistemas internos",
                  category="Ética"),
    ],
    channels=[
        ChannelConfig(
            id="whatsapp", name="WhatsApp", formalityLevel=30, greeting="Oi, {nome}! 👋",
            maxLength=320, useEmoji=True,
            guidelines=["Use linguagem informal e amigável",
                        "Incluir emojis relevantes com moderação",
                        "Mensagens curtas e diretas",
                        "Botões de resposta rápida quando possível"],
            sampleMessage="Oi, Maria! 👋 Vi que você quer alterar seu plano. Posso te ajudar!",
            presentation=ChannelPresentation(color="text-green-600", bgColor="bg-green-50",
                                             iconColor="bg-green-50"),
        ),
        ChannelConfig(
            id="webchat", name="Web Chat", formalityLevel=55, greeting="Olá, {nome}!",
            maxLength=420, useEmoji=False,
            guidelines=["Tom profissional e estruturado",
                        "Sem emojis, usar formatação de texto",
                        "Links clicáveis quando necessário",
                        "Mensagens detalhadas são aceitáveis"],
            sampleMessage=("Olá, Maria! Vejo que gostaria de alterar seu plano. "
                           "Ficarei feliz em auxiliar você neste processo."),
            presentation=ChannelPresentation(color="text-blue-600", bgColor="bg-blue-50",
                                             iconColor="bg-blue-50"),
        ),
        ChannelConfig(
            id="app", name="App Claro", formalityLevel=45, greeting="Olá, {nome}",
            maxLength=360, useEmoji=False,
            guidelines=["Tom moderno e direto",
                        "Aproveitar componentes nativos do app",
                        "Integrar ações contextuais do app",
                        "Notificações push para acompanhamento"],
            sampleMessage="Olá, Maria. Quer alterar seu plano? Veja as opções disponíveis.",
            presentation=ChannelPresentation(color="text-red-600", bgColor="bg-red-50",
                                             iconColor="bg-red-50"),
        ),
        ChannelConfig(
            id="voice", name="Voz (URA)", formalityLevel=50, greeting="", maxLength=200,
            useEmoji=False, guidelines=[], sampleMessage="",
            presentation=ChannelPresentation(color="text-purple-600", bgColor="bg-purple-50",
                                             iconColor="bg-purple-50"),
            voiceConfig=VOICE_DEFAULTS,
        ),
    ],
)


def _timeline(entries: list[tuple[str, str, str]]) -> list[TimelineEvent]:
    return [TimelineEvent(date=d, event=e, type=t) for d, e, t in entries]


# ------------------------------------------------------------------ clientes
def _customers() -> list[Customer]:
    now = utcnow()
    return [
        Customer(
            id="cust_maria_silva", name="Maria Silva Santos",
            document_masked="***.***.***-42", birth_date="15/03/1985",
            customer_since="Janeiro 2023", segment="VIP",
            email="maria.silva@email.com", phone="(11) 98765-4321",
            preferred_channel=Channel.whatsapp,
            plan=Plan(name="Claro Flex 30GB", price=79.90, data_gb=30, used_gb=25.5,
                      line="(11) 98765-4321", due_day=10),
            products=[
                {"name": "Claro Flex 30GB", "status": "Ativo",
                 "description": "Linha móvel • (11) 98765-4321"},
                {"name": "Claro TV+ 100 canais", "status": "Ativo",
                 "description": "TV por assinatura"},
                {"name": "Claro Internet 500MB", "status": "Ativo",
                 "description": "Internet residencial"},
            ],
            timeline=_timeline([
                ("15/05/2026 09:15", "Consultou segunda via de fatura no App", "app"),
                ("10/05/2026 16:45", "Atendimento técnico — sinal restabelecido", "support"),
                ("28/04/2026 11:20", "Pagamento de fatura em dia", "payment"),
                ("15/04/2026 14:00", "Upgrade de plano 20GB → 30GB", "plan"),
            ]),
            churn_risk=0.12,
            churn_factors=[
                {"text": "Pagamentos pontuais", "positive": True},
                {"text": "Alta utilização de serviços", "positive": True},
                {"text": "Engajamento recente", "positive": True},
            ],
            aliases={"whatsapp": "5511987654321", "web": "sess-web-maria",
                     "app": "device-maria-01"},
            persona_summary=("Resolve tudo pelo celular e troca de canal no meio da "
                             "conversa. Direta, não gosta de repetir informação. "
                             "Está perto de estourar a franquia."),
            marketing_opt_in=True,
            last_inbound_at=now - timedelta(hours=2),
        ),
        Customer(
            id="cust_carla_mendes", name="Carla Mendes", segment="Padrão",
            customer_since="Março 2024", email="carla.mendes@email.com",
            phone="(21) 99612-8877", preferred_channel=Channel.whatsapp,
            plan=Plan(name="Claro Internet 300MB", price=99.90, data_gb=300, used_gb=180,
                      line="Residencial", due_day=20),
            products=[{"name": "Claro Internet 300MB", "status": "Ativo",
                       "description": "Internet residencial"}],
            timeline=_timeline([
                ("22/05/2026 21:10", "Reclamação de lentidão à noite", "support"),
                ("02/05/2026 08:30", "Visita técnica realizada", "support"),
            ]),
            churn_risk=0.38,
            churn_factors=[
                {"text": "Dois chamados técnicos em 30 dias", "positive": False},
                {"text": "Pagamentos em dia", "positive": True},
            ],
            aliases={"whatsapp": "5521996128877"},
            persona_summary=("Procura suporte fora do horário comercial, geralmente "
                             "à noite. Impaciente com diagnóstico repetido: se já "
                             "reiniciou o roteador, não quer ouvir isso de novo."),
            marketing_opt_in=False,
            last_inbound_at=now - timedelta(days=2),
        ),
        Customer(
            id="cust_juliana_rocha", name="Juliana Rocha", segment="Padrão",
            customer_since="Agosto 2025", email="juliana.rocha@email.com",
            phone="(31) 98123-4455", preferred_channel=Channel.app,
            plan=Plan(name="Claro Flex 20GB", price=59.90, data_gb=20, used_gb=9.4,
                      line="(31) 98123-4455", due_day=5),
            products=[{"name": "Claro Flex 20GB", "status": "Ativo",
                       "description": "Linha móvel • (31) 98123-4455"}],
            timeline=_timeline([
                ("18/05/2026 12:02", "Baixou segunda via pelo app", "app"),
                ("18/04/2026 12:00", "Baixou segunda via pelo app", "app"),
            ]),
            churn_risk=0.15,
            churn_factors=[{"text": "Uso estável do autosserviço", "positive": True}],
            aliases={"app": "device-juliana-77", "whatsapp": "5531981234455"},
            persona_summary=("Prefere resolver sozinha pelo app. Objetiva, escreve "
                             "pouco. Cada atendimento dela que vira humano é custo "
                             "que poderia ter sido evitado."),
            marketing_opt_in=True,
            last_inbound_at=now - timedelta(days=12),
        ),
        Customer(
            id="cust_felipe_barros", name="Felipe Barros", segment="Padrão",
            customer_since="Fevereiro 2021", email="felipe.barros@email.com",
            phone="(11) 97788-1234", preferred_channel=Channel.whatsapp,
            plan=Plan(name="Claro Flex 50GB", price=99.90, data_gb=50, used_gb=41,
                      line="(11) 97788-1234", due_day=15),
            products=[
                {"name": "Claro Flex 50GB", "status": "Ativo", "description": "Linha móvel"},
                {"name": "Claro TV+ 60 canais", "status": "Ativo",
                 "description": "TV por assinatura"},
            ],
            timeline=_timeline([
                ("20/05/2026 19:40", "Reclamou de cobrança indevida", "payment"),
                ("11/05/2026 10:15", "Chamado técnico sem resolução", "support"),
            ]),
            churn_risk=0.71,
            churn_factors=[
                {"text": "Reclamação de cobrança em aberto", "positive": False},
                {"text": "Chamado técnico não resolvido", "positive": False},
            ],
            aliases={"whatsapp": "5511977881234"},
            persona_summary=("Chega irritado e com histórico de atrito. Quer ser ouvido "
                             "antes de qualquer oferta — proposta comercial cedo demais "
                             "piora a conversa."),
            marketing_opt_in=False,
            last_inbound_at=now - timedelta(hours=30),
        ),
        Customer(
            id="cust_joao_santos", name="João Santos", segment="Padrão",
            customer_since="Julho 2024", phone="(41) 99555-2211",
            preferred_channel=Channel.whatsapp,
            plan=Plan(name="Claro Flex 30GB", price=79.90, data_gb=30, used_gb=27.8,
                      line="(41) 99555-2211", due_day=25),
            products=[{"name": "Claro Flex 30GB", "status": "Ativo",
                       "description": "Linha móvel"}],
            churn_risk=0.22,
            aliases={"whatsapp": "5541995552211"},
            persona_summary=("Está trazendo o número de outra operadora. Faz muitas "
                             "perguntas sobre prazo e portabilidade."),
            marketing_opt_in=True,
            last_inbound_at=now - timedelta(hours=6),
        ),
        Customer(
            id="cust_ricardo_lima", name="Ricardo Lima", segment="Padrão",
            customer_since="Novembro 2025", phone="(51) 98444-3322",
            preferred_channel=Channel.web,
            plan=Plan(name="Claro Flex 20GB", price=59.90, data_gb=20, used_gb=17.2,
                      line="(51) 98444-3322", due_day=8),
            products=[{"name": "Claro Flex 20GB", "status": "Ativo",
                       "description": "Linha móvel"}],
            churn_risk=0.19,
            aliases={"web": "sess-web-ricardo"},
            persona_summary=("Pesquisa antes de decidir. Quer comparar planos família "
                             "e entender o custo total antes de mudar."),
            marketing_opt_in=True,
            last_inbound_at=now - timedelta(days=4),
        ),
    ]


async def populate(customers, conversations, studio) -> None:
    """Idempotente: se já houver cadastro, nada é recriado."""
    existing = await customers.all()
    if existing:
        return

    await studio.save(DEFAULT_STUDIO)
    for customer in _customers():
        await customers.save(customer)
