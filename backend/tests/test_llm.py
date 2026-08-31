"""Testes da camada de IA.

Toda a rede é substituída por dublês: um teste que depende de uma chave de API
falha na máquina de quem não tem a chave, o que é o mesmo que não existir. O que
se verifica aqui é o *contrato* do adaptador — o que ele monta, o que ele
interpreta e o que ele faz quando o provedor falha.
"""
from __future__ import annotations

import httpx
import pytest

from app.domain.ports.response_generator import GenerationRequest
from app.domain.studio import ChannelConfig, Guardrail, Persona, StudioConfig
from app.domain.value_objects.area import Area
from app.domain.value_objects.channel import Channel
from app.domain.value_objects.intent import Intent
from app.domain.value_objects.intent_engine import IntentEngine
from app.domain.value_objects.response_source import ResponseSource
from app.infrastructure.llm.llm_client import LLMClient, LLMUnavailable
from app.infrastructure.llm.llm_intent_classifier import LLMIntentClassifier
from app.infrastructure.llm.llm_response_generator import LLMResponseGenerator
from app.infrastructure.llm.prompt_loader import PromptLoader, PromptNotFound
from app.infrastructure.llm.resilient_intent_classifier import ResilientIntentClassifier
from app.infrastructure.llm.resilient_response_generator import ResilientResponseGenerator
from app.infrastructure.llm.rule_based_classifier import RuleBasedIntentClassifier
from app.infrastructure.llm.template_response_generator import TemplateResponseGenerator
from app.infrastructure.llm.text_cleanup import clean_reply
from app.settings import LLMSettings

VENDA = Intent(slug="alteracao_plano", name="Alteração de Plano",
               confidence=0.9, area=Area.vendas)


def studio() -> StudioConfig:
    return StudioConfig(
        persona=Persona(name="Clara", description="Assistente da Claro",
                        traits=["clara", "direta"]),
        guardrails=[Guardrail(rule="Nunca prometer o que não pode cumprir",
                              category="Ética")],
        channels=[ChannelConfig(id="whatsapp", name="WhatsApp", formalityLevel=30,
                                greeting="Oi, {nome}!", maxLength=160, useEmoji=True)],
    )


def request(**overrides) -> GenerationRequest:
    base = dict(channel=Channel.whatsapp, intent=VENDA, config=studio(),
                customer_message="quero mais internet",
                fallback_text="Posso te ajudar com isso.")
    return GenerationRequest(**{**base, **overrides})


# ============================================================== cliente HTTP
class FakeTransport(httpx.AsyncBaseTransport):
    """Responde no lugar do provedor, sem tocar na rede."""

    def __init__(self, status: int = 200, payload: dict | None = None) -> None:
        self.status = status
        self.payload = payload if payload is not None else {
            "choices": [{"message": {"content": "Tudo certo!"}}]
        }
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        return httpx.Response(self.status, json=self.payload, request=req)


@pytest.fixture
def llm_settings() -> LLMSettings:
    return LLMSettings(base_url="https://api.exemplo/v1", model="modelo-x",
                       api_key="chave-de-teste")


def patched_client(monkeypatch, transport: httpx.AsyncBaseTransport) -> None:
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


class TestLLMClient:
    async def test_recusa_quando_nao_ha_chave_configurada(self):
        client = LLMClient(LLMSettings(api_key=""))

        with pytest.raises(LLMUnavailable, match="chave"):
            await client.complete("oi")

    async def test_fala_o_protocolo_openai_no_caminho_correto(self, monkeypatch, llm_settings):
        transport = FakeTransport()
        patched_client(monkeypatch, transport)

        text = await LLMClient(llm_settings).complete("oi", system="seja breve")

        assert text == "Tudo certo!"
        enviado = transport.requests[0]
        assert str(enviado.url) == "https://api.exemplo/v1/chat/completions"
        assert enviado.headers["authorization"] == "Bearer chave-de-teste"

    async def test_envia_o_sistema_antes_da_mensagem_do_usuario(self, monkeypatch, llm_settings):
        import json
        transport = FakeTransport()
        patched_client(monkeypatch, transport)

        await LLMClient(llm_settings).complete("pergunta", system="instrução")

        corpo = json.loads(transport.requests[0].content)
        assert corpo["messages"][0] == {"role": "system", "content": "instrução"}
        assert corpo["messages"][1] == {"role": "user", "content": "pergunta"}
        assert corpo["model"] == "modelo-x"

    async def test_repassa_os_parametros_extras_do_provedor(self, monkeypatch):
        """Um modelo de raciocínio devolve o raciocínio junto se ninguém pedir
        o contrário — e esse texto não pode chegar ao cliente."""
        import json
        transport = FakeTransport()
        patched_client(monkeypatch, transport)
        settings = LLMSettings(base_url="https://api.groq.com/openai/v1",
                               model="openai/gpt-oss-120b", api_key="gsk_teste")
        object.__setattr__(settings, "extra_params",
                           {"include_reasoning": False, "reasoning_effort": "low"})

        await LLMClient(settings).complete("oi")

        corpo = json.loads(transport.requests[0].content)
        assert corpo["include_reasoning"] is False
        assert corpo["reasoning_effort"] == "low"
        assert corpo["model"] == "openai/gpt-oss-120b"

    async def test_sem_parametros_extras_o_corpo_fica_no_protocolo_padrao(
            self, monkeypatch, llm_settings):
        import json
        transport = FakeTransport()
        patched_client(monkeypatch, transport)

        await LLMClient(llm_settings).complete("oi")

        corpo = json.loads(transport.requests[0].content)
        assert set(corpo) == {"model", "messages", "temperature", "max_tokens"}

    async def test_erro_http_vira_indisponibilidade(self, monkeypatch, llm_settings):
        patched_client(monkeypatch, FakeTransport(status=429))

        with pytest.raises(LLMUnavailable):
            await LLMClient(llm_settings).complete("oi")

    async def test_resposta_fora_do_contrato_vira_indisponibilidade(self, monkeypatch,
                                                                    llm_settings):
        patched_client(monkeypatch, FakeTransport(payload={"sem": "choices"}))

        with pytest.raises(LLMUnavailable):
            await LLMClient(llm_settings).complete("oi")


# ====================================================== classificador por IA
class FakeLLM:
    def __init__(self, reply: str = "", fail: bool = False) -> None:
        self.reply = reply
        self.fail = fail
        self.prompts: list[str] = []
        self.model = "modelo-x"
        self.enabled = True

    async def complete(self, prompt, **_kwargs) -> str:
        self.prompts.append(prompt)
        if self.fail:
            raise LLMUnavailable("provedor fora do ar")
        return self.reply


class TestClassificadorPorIA:
    async def test_interpreta_o_json_do_modelo(self):
        llm = FakeLLM('{"slug": "alteracao_plano", "confidence": 0.93, '
                      '"reasoning": "pediu upgrade"}')

        intent = await LLMIntentClassifier(llm, PromptLoader()).classify("quero mais gb")

        assert intent.slug == "alteracao_plano"
        assert intent.confidence == 0.93
        assert intent.engine is IntentEngine.llm
        assert intent.reasoning == "pediu upgrade"

    async def test_aceita_json_embrulhado_em_texto(self):
        llm = FakeLLM('Claro! Aqui está:\n```json\n{"slug": "suporte_tecnico"}\n```')

        intent = await LLMIntentClassifier(llm, PromptLoader()).classify("internet lenta")

        assert intent.slug == "suporte_tecnico"

    async def test_recusa_slug_fora_da_taxonomia(self):
        llm = FakeLLM('{"slug": "pedir_pizza"}')

        with pytest.raises(LLMUnavailable, match="taxonomia"):
            await LLMIntentClassifier(llm, PromptLoader()).classify("oi")

    async def test_recusa_resposta_sem_json(self):
        llm = FakeLLM("não sei responder")

        with pytest.raises(LLMUnavailable):
            await LLMIntentClassifier(llm, PromptLoader()).classify("oi")

    async def test_recusa_json_malformado(self):
        llm = FakeLLM('{"slug": "alteracao_plano",}')

        with pytest.raises(LLMUnavailable, match="JSON"):
            await LLMIntentClassifier(llm, PromptLoader()).classify("oi")

    async def test_limita_a_confianca_ao_intervalo_valido(self):
        llm = FakeLLM('{"slug": "alteracao_plano", "confidence": 3.5}')

        intent = await LLMIntentClassifier(llm, PromptLoader()).classify("oi")

        assert intent.confidence == 1.0

    async def test_o_catalogo_do_prompt_vem_do_design_studio(self):
        from app.domain.studio.configured_intent import ConfiguredIntent
        config = studio()
        config.intents = [ConfiguredIntent(slug="alteracao_plano", name="Trocar de plano",
                                           confidence="Alta", examples="quero mais gb")]
        llm = FakeLLM('{"slug": "alteracao_plano"}')

        await LLMIntentClassifier(llm, PromptLoader(), studio=config).classify("oi")

        assert "Trocar de plano" in llm.prompts[0]

    async def test_o_historico_recente_entra_no_prompt(self):
        llm = FakeLLM('{"slug": "alteracao_plano"}')

        await LLMIntentClassifier(llm, PromptLoader()).classify(
            "pode prosseguir", history=["quero mudar de plano", "qual plano?"])

        assert "quero mudar de plano" in llm.prompts[0]


# ============================================================ redator por IA
class TestRedatorPorIA:
    async def test_monta_o_prompt_com_persona_canal_e_objetivo(self):
        llm = FakeLLM("Claro! Posso te mostrar as opções.")

        await LLMResponseGenerator(llm, PromptLoader()).generate(
            request(directive="Apresentar o plano com mais franquia."))

        prompt = llm.prompts[0]
        assert "Clara" in prompt
        assert "WhatsApp" in prompt
        assert "Apresentar o plano com mais franquia." in prompt
        assert "Nunca prometer o que não pode cumprir" in prompt

    async def test_marca_a_resposta_como_generativa(self):
        llm = FakeLLM("Posso te mostrar as opções.")

        resposta = await LLMResponseGenerator(llm, PromptLoader()).generate(request())

        assert resposta.source is ResponseSource.generative
        assert resposta.model == "modelo-x"

    async def test_limpa_o_que_o_modelo_embrulha(self):
        llm = FakeLLM('"Clara: Posso te ajudar com isso."')

        resposta = await LLMResponseGenerator(llm, PromptLoader()).generate(request())

        assert resposta.text == "Posso te ajudar com isso."

    async def test_resposta_vazia_conta_como_falha(self):
        llm = FakeLLM("   ")

        with pytest.raises(LLMUnavailable, match="vazia"):
            await LLMResponseGenerator(llm, PromptLoader()).generate(request())

    async def test_descreve_o_cliente_para_o_modelo(self):
        from app.domain.entities.customer import Customer
        from app.domain.entities.plan import Plan
        llm = FakeLLM("ok")
        cliente = Customer(id="c1", name="Maria Silva", segment="VIP",
                           persona_summary="Estoura a franquia todo mês",
                           plan=Plan(name="Flex 30GB", price=79.9, data_gb=30, used_gb=27.6))

        await LLMResponseGenerator(llm, PromptLoader()).generate(request(customer=cliente))

        prompt = llm.prompts[0]
        assert "Maria" in prompt
        assert "Flex 30GB" in prompt
        assert "Estoura a franquia todo mês" in prompt

    async def test_descreve_os_dados_dos_sistemas_internos(self):
        llm = FakeLLM("ok")

        await LLMResponseGenerator(llm, PromptLoader()).generate(request(
            business_facts={"catalogo": {"planos": [{"nome": "Flex 50GB", "preco": 99.9}]}}))

        prompt = llm.prompts[0]
        assert "catalogo" in prompt
        assert "Flex 50GB" in prompt
        assert "99,90" in prompt

    async def test_leva_a_conversa_ate_aqui_para_o_modelo(self):
        llm = FakeLLM("ok")

        await LLMResponseGenerator(llm, PromptLoader()).generate(request(
            transcript=[{"author": "customer", "text": "quero mudar de plano"},
                        {"author": "bot", "text": "posso ajudar"}]))

        assert "Cliente: quero mudar de plano" in llm.prompts[0]


# ===================================================== redator determinístico
class TestRedatorDeterministico:
    async def test_usa_o_texto_de_reserva_quando_informado(self):
        resposta = await TemplateResponseGenerator().generate(
            request(fallback_text="Sua fatura vence dia 10."))

        assert resposta.text == "Sua fatura vence dia 10."
        assert resposta.source is ResponseSource.template
        assert resposta.model is None

    async def test_responde_algo_util_mesmo_sem_texto_de_reserva(self):
        resposta = await TemplateResponseGenerator().generate(
            request(fallback_text=""))

        assert resposta.text
        assert resposta.source is ResponseSource.template

    def test_declara_que_nao_e_generativo(self):
        assert TemplateResponseGenerator().uses_generative_ai is False


# ============================================================= encadeamentos
class TestEncadeamentos:
    async def test_classificador_cai_para_regras_quando_a_ia_falha(self):
        chain = ResilientIntentClassifier(FailingClassifier(), RuleBasedIntentClassifier())

        intent = await chain.classify("quero mudar meu plano")

        assert intent.engine is IntentEngine.rules
        assert chain.last_engine == RuleBasedIntentClassifier().engine_name

    async def test_classificador_usa_a_ia_quando_ela_responde(self):
        llm = FakeLLM('{"slug": "alteracao_plano"}')
        primary = LLMIntentClassifier(llm, PromptLoader())
        chain = ResilientIntentClassifier(primary, RuleBasedIntentClassifier())

        intent = await chain.classify("quero mudar meu plano")

        assert intent.engine is IntentEngine.llm
        assert chain.last_engine == primary.engine_name

    async def test_redator_cai_para_o_modelo_de_texto_quando_a_ia_falha(self):
        chain = ResilientResponseGenerator(
            LLMResponseGenerator(FakeLLM(fail=True), PromptLoader()),
            TemplateResponseGenerator())

        resposta = await chain.generate(request(fallback_text="Posso te ajudar."))

        assert resposta.source is ResponseSource.template
        assert resposta.text == "Posso te ajudar."

    async def test_redator_usa_a_ia_quando_ela_responde(self):
        chain = ResilientResponseGenerator(
            LLMResponseGenerator(FakeLLM("Escrito pela IA."), PromptLoader()),
            TemplateResponseGenerator())

        resposta = await chain.generate(request())

        assert resposta.source is ResponseSource.generative
        assert resposta.text == "Escrito pela IA."

    def test_o_nome_do_encadeamento_mostra_os_dois_elos(self):
        chain = ResilientIntentClassifier(FailingClassifier(), RuleBasedIntentClassifier())
        assert "→" in chain.engine_name


class FailingClassifier(RuleBasedIntentClassifier):
    @property
    def engine_name(self) -> str:
        return "IA (indisponível)"

    async def classify(self, text: str, *, history=None):
        raise LLMUnavailable("fora do ar")


# ============================================================ classificador por regras
class TestClassificadorPorRegras:
    async def test_reconhece_as_intencoes_do_catalogo(self):
        classifier = RuleBasedIntentClassifier()

        casos = {
            "quero mudar meu plano": "alteracao_plano",
            "preciso da segunda via da fatura": "segunda_via_fatura",
            "minha internet está lenta": "suporte_tecnico",
            "quero falar com um atendente": "falar_atendente",
        }
        for texto, slug in casos.items():
            assert (await classifier.classify(texto)).slug == slug

    async def test_confessa_quando_nao_entende(self):
        intent = await RuleBasedIntentClassifier().classify("xyzzy plugh")

        assert intent.slug == "nao_identificada"
        assert intent.is_confident is False

    async def test_extrai_entidades_do_texto(self):
        intent = await RuleBasedIntentClassifier().classify("quero o Claro Flex 50GB")

        assert intent.entities


# ================================================================= utilidades
class TestLimpezaDeTexto:
    @pytest.mark.parametrize("bruto,limpo", [
        ('"Posso te ajudar."', "Posso te ajudar."),
        ("Clara: Posso te ajudar.", "Posso te ajudar."),
        ("```\nPosso te ajudar.\n```", "Posso te ajudar."),
        ("**Posso** te ajudar.", "Posso te ajudar."),
        ("## Posso te ajudar.", "Posso te ajudar."),
        ("Posso   te ajudar.", "Posso te ajudar."),
        ("", ""),
    ])
    def test_remove_o_embrulho_do_modelo(self, bruto, limpo):
        assert clean_reply(bruto) == limpo


class TestRaciocinioNaoChegaAoCliente:
    """Rede de segurança para modelos de raciocínio.

    O certo é desligar o raciocínio no pedido, por `LLM_EXTRA_PARAMS`. Mas o
    parâmetro varia de provedor para provedor e já houve relato de vazamento
    mesmo desligado — e um cliente da Claro lendo o monólogo interno do robô é
    pior do que qualquer regex.
    """

    def test_remove_o_bloco_de_raciocinio_e_mantem_a_resposta(self):
        bruto = ("<think>O cliente usa 85% da franquia. Devo oferecer o Flex 50GB, "
                 "mas sem prometer preço que não veio do catálogo.</think>"
                 "Oi, Maria! Vi que você está perto de estourar a franquia.")

        assert clean_reply(bruto) == "Oi, Maria! Vi que você está perto de estourar a franquia."

    @pytest.mark.parametrize("tag", ["think", "thinking", "reasoning"])
    def test_reconhece_as_variacoes_de_marcador(self, tag):
        assert clean_reply(f"<{tag}>pensando alto</{tag}>Resposta.") == "Resposta."

    def test_no_formato_harmony_fica_so_o_canal_final(self):
        bruto = ("<|start|>assistant<|channel|>analysis<|message|>preciso checar o plano"
                 "<|end|><|start|>assistant<|channel|>final<|message|>"
                 "Claro, posso te ajudar!<|return|>")

        assert clean_reply(bruto) == "Claro, posso te ajudar!"

    def test_raciocinio_cortado_no_meio_nao_vira_resposta(self):
        """Sem `</think>` o limite de tokens cortou o raciocínio: não sobrou
        resposta, e vazio faz o redator de reserva assumir."""
        assert clean_reply("<think>Deixa eu pensar, o cliente pediu") == ""

    def test_texto_limpo_atravessa_sem_alteracao(self):
        assert clean_reply("Oi, Maria! Tudo certo por aqui.") == "Oi, Maria! Tudo certo por aqui."


class TestCarregadorDePrompts:
    def test_le_os_prompts_do_projeto(self):
        loader = PromptLoader()

        assert "response_generation" in loader.available()
        assert loader.raw("response_generation")

    def test_substitui_as_variaveis(self):
        loader = PromptLoader()

        texto = loader.render("response_generation", persona_nome="Clarice")

        assert "Clarice" in texto
        assert "{{persona_nome}}" not in texto

    def test_prompt_inexistente_falha_de_forma_explicita(self):
        with pytest.raises(PromptNotFound):
            PromptLoader().raw("prompt_que_nao_existe")
