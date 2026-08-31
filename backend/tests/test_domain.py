"""Testes das regras de domínio.

Rodam sem Redis, sem MongoDB, sem rede e sem FastAPI — que é justamente o
ponto de manter a regra de negócio fora da infraestrutura.
"""
import pytest

from app.domain.entities import Conversation
from app.domain.services.handover_policy import HandoverPolicy
from app.domain.services.intent_continuity import IntentContinuityService
from app.domain.services.persona_service import PersonaService
from app.domain.services.routing_service import Flow, RoutingService
from app.domain.studio import ChannelConfig, StudioConfig
from app.domain.value_objects import Area, Channel, Intent, IntentEngine

VENDA = Intent(slug="alteracao_plano", name="Alteração de Plano",
               confidence=0.95, area=Area.vendas)
VAGA = Intent(slug="nao_identificada", name="Não Identificada",
              confidence=0.25, area=Area.suporte)
ATENDENTE = Intent(slug="falar_atendente", name="Falar com Atendente",
                   confidence=0.9, area=Area.suporte)


def conversation() -> Conversation:
    return Conversation(session_id="s1", customer_id="c1", customer_name="Maria")


# ------------------------------------------------------------------ persona
def studio(**channel_overrides) -> StudioConfig:
    base = {"id": "whatsapp", "name": "WhatsApp", "formalityLevel": 30,
            "greeting": "Oi, {nome}!", "maxLength": 160, "useEmoji": True}
    return StudioConfig(channels=[ChannelConfig(**{**base, **channel_overrides})])


def test_persona_remove_emoji_quando_canal_nao_permite():
    result = PersonaService().apply("Tudo certo! 👋😄", studio(useEmoji=False), Channel.whatsapp)
    assert "👋" not in result and "😄" not in result
    assert result.startswith("Tudo certo!")


def test_persona_nao_deixa_pontuacao_orfa_sem_nome():
    """Cliente anônimo é o caso comum no primeiro contato de um canal aberto."""
    result = PersonaService().apply("Como posso ajudar?", studio(), Channel.whatsapp,
                                    customer_first_name="", greet=True)
    assert result.startswith("Oi!")
    assert "Oi, !" not in result


def test_persona_interpola_nome_quando_existe():
    result = PersonaService().apply("Como posso ajudar?", studio(), Channel.whatsapp,
                                    customer_first_name="Maria", greet=True)
    assert result.startswith("Oi, Maria!")


def test_persona_trunca_em_fronteira_de_frase():
    """Áudio da URA cortado no meio de uma palavra é pior do que áudio curto."""
    texto = "Primeira frase completa. Segunda frase que estoura o limite estabelecido."
    result = PersonaService().apply(texto, studio(maxLength=40, useEmoji=False), Channel.whatsapp)
    assert len(result) <= 40
    assert result.endswith(".")


# ------------------------------------------------------------- roteamento
def test_roteamento_leva_alteracao_de_plano_para_venda():
    route = RoutingService.route(VENDA)
    assert route.flow is Flow.venda
    assert "catalogo_planos" in route.services


def test_intencao_incerta_nao_aciona_sistema_interno():
    """Agir sobre um palpite ruim custa mais caro do que perguntar de novo."""
    route = RoutingService.route(VAGA)
    assert route.flow is Flow.fallback
    assert route.services == ()


# --------------------------------------------------------------- handover
def test_handover_quando_cliente_pede_atendente():
    decision = HandoverPolicy().evaluate(ATENDENTE, "quero falar com atendente", conversation())
    assert decision.should_handover


def test_handover_por_insatisfacao_detectada():
    decision = HandoverPolicy().evaluate(VENDA, "isso e um absurdo", conversation())
    assert decision.should_handover
    assert "nsatisfação" in decision.reason


def test_baixa_confianca_isolada_nao_escala():
    """Não entender uma mensagem rende uma pergunta, não uma transferência.

    Escalar no primeiro tropeço faria do hub um encaminhador de fila — e o
    cliente ainda teria de repetir tudo para o atendente."""
    decision = HandoverPolicy().evaluate(VAGA, "hmm", conversation())
    assert not decision.should_handover


def test_handover_por_baixa_confianca_repetida():
    decision = HandoverPolicy().evaluate(VAGA, "hmm", conversation(),
                                         consecutive_failures=2)
    assert decision.should_handover
    assert "confiança" in decision.reason


def test_sem_handover_no_caminho_feliz():
    assert not HandoverPolicy().evaluate(VENDA, "quero mudar de plano", conversation()).should_handover


# ------------------------------------------------------------ continuidade
def test_mensagem_sem_sinal_herda_o_assunto_da_conversa():
    """'pode prosseguir' não muda de assunto."""
    result = IntentContinuityService().reconcile(VAGA, VENDA)
    assert result.slug == "alteracao_plano"
    assert "herdado" in result.reasoning


def test_classificacao_confiante_troca_o_assunto():
    nova = Intent(slug="cancelamento", name="Cancelamento", confidence=0.9, area=Area.retencao)
    assert IntentContinuityService().reconcile(nova, VENDA).slug == "cancelamento"


def test_entidade_nova_sobrevive_a_heranca():
    parcial = VAGA.model_copy(update={"entities": {"plano": "Claro Flex 60GB"}})
    result = IntentContinuityService().reconcile(parcial, VENDA)
    assert result.entities["plano"] == "Claro Flex 60GB"


# ------------------------------------------------------------- agregado
def test_pedir_atendente_nao_muda_a_area_do_caso():
    """Um caso de Vendas continua sendo de Vendas depois do transbordo."""
    conv = conversation()
    conv.apply_intent(VENDA)
    conv.apply_intent(ATENDENTE, governs_area=False)
    assert conv.area is Area.vendas


def test_troca_de_canal_e_detectada():
    conv = conversation()
    conv.record_message("oi", Channel.web, from_customer=True)
    conv.record_message("continuo aqui", Channel.whatsapp, from_customer=True)
    assert conv.channels_used == [Channel.web, Channel.whatsapp]


def test_conversa_transferida_nao_volta_sozinha_ao_bot():
    conv = conversation()
    conv.request_handover("cliente pediu", [], 5)
    conv.request_handover("outro motivo", [], 9)
    assert conv.handover.reason == "cliente pediu"


def test_atribuir_atendente_sem_handover_e_erro():
    with pytest.raises(ValueError):
        conversation().assign_agent("Ana")


# ---------------------------------------- regressões da etapa 10
def test_mensagem_herdada_nao_dispara_transbordo():
    """'pode prosseguir' herda o assunto — não é motivo para escalar."""
    herdada = IntentContinuityService().reconcile(VAGA, VENDA)
    decision = HandoverPolicy().evaluate(herdada, "pode prosseguir", conversation(),
                                         consecutive_failures=1)
    assert not decision.should_handover


def test_incompreensao_repetida_escala():
    decision = HandoverPolicy().evaluate(VENDA, "asdfgh", conversation(),
                                         consecutive_failures=3)
    assert decision.should_handover
    assert "três tentativas" in decision.reason.lower()


def test_sessao_conta_falhas_consecutivas():
    from app.domain.entities import Session
    s = Session(conversation_id="c", customer_id="x")
    assert s.register_classification(False) == 1
    assert s.register_classification(False) == 2
    assert s.register_classification(True) == 0


def test_confirmacao_avanca_em_vez_de_repetir_a_oferta():
    """O bot não pode reapresentar a mesma oferta a cada turno."""
    from app.domain.services.reply_composer import ReplyComposer
    from app.domain.services.routing_service import Flow

    intent = VENDA.model_copy(update={"entities": {"plano": "Claro Flex 50GB"}})
    data = {"catalogo_planos": {"upgrades": [
        {"name": "Claro Flex 50GB", "price": 99.90, "data_gb": 50}]}}

    oferta = ReplyComposer().compose(Flow.venda, intent, data, "Claro Flex 30GB",
                                     text="quero o Claro Flex 50GB")
    confirmacao = ReplyComposer().compose(Flow.venda, intent, data, "Claro Flex 30GB",
                                          text="sim, pode prosseguir")
    assert oferta != confirmacao
    assert "registrando a alteração" in confirmacao


def test_conversa_transferida_continua_sendo_a_corrente():
    """Depois do transbordo o cliente continua escrevendo, e essas mensagens
    têm de chegar ao atendente — não abrir uma conversa nova."""
    conv = conversation()
    conv.request_handover("cliente pediu", [], 3)
    assert conv.with_human
    assert conv.is_current      # continua sendo a conversa vigente
    assert not conv.is_open     # mas não é mais conduzida pelo bot
