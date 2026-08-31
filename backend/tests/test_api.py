"""Testes de contrato da API.

Percorrem a pilha inteira — roteador, esquema, caso de uso, domínio, repositório
— com adaptadores em memória. É o teste que responde à pergunta que a banca vai
fazer: "isso funciona de ponta a ponta?".
"""
from __future__ import annotations

from conftest import send


# ============================================================ ingestão de canais
class TestIngestao:
    def test_responde_ao_cliente_identificado_pelo_id_interno(self, client, maria):
        response = send(client, "whatsapp", "Quero aumentar minha franquia", maria.id)

        assert response.status_code == 200
        body = response.json()
        assert body["customer_id"] == maria.id
        assert body["reply"]
        assert body["intent"]["name"]
        assert body["turns"] == 1

    def test_resolve_o_cliente_pelo_identificador_do_canal(self, client):
        response = send(client, "whatsapp", "oi", external_id="+5511999990001")

        assert response.status_code == 200
        assert response.json()["customer_id"]

    def test_a_mesma_conversa_continua_na_segunda_mensagem(self, client, maria):
        send(client, "web", "Quero mudar de plano", maria.id)
        second = send(client, "web", "pode prosseguir", maria.id)

        assert second.json()["turns"] == 2

    def test_classifica_a_intencao_e_informa_o_motor_usado(self, client, maria):
        body = send(client, "web", "minha internet está lenta", maria.id).json()

        assert body["intent"]["slug"]
        assert body["intent"]["engine"] == "rules"
        assert 0 <= body["intent"]["confidence"] <= 1

    def test_consulta_os_sistemas_internos_do_fluxo(self, client, maria):
        body = send(client, "web", "quero a segunda via da fatura", maria.id).json()

        assert body["flow"]
        assert isinstance(body["services_consulted"], list)

    def test_recusa_o_atendimento_sem_consentimento(self, client, maria):
        response = client.post("/api/v1/channels/web/messages", json={
            "text": "oi", "customer_id": maria.id,
            "consent": {"granted": False, "scope": []},
        })

        assert response.status_code == 403
        assert "consentimento" in response.json()["detail"].lower()

    def test_rejeita_canal_inexistente(self, client, maria):
        assert send(client, "telegrama", "oi", maria.id).status_code == 422

    def test_rejeita_mensagem_vazia(self, client, maria):
        response = client.post("/api/v1/channels/web/messages",
                               json={"text": "", "customer_id": maria.id})
        assert response.status_code == 422

    def test_lista_os_canais_e_marca_quais_podem_ser_simulados(self, client):
        canais = client.get("/api/v1/channels").json()

        por_id = {c["channel"]: c for c in canais}
        assert por_id["whatsapp"]["simulatable"] is True
        assert por_id["voice"]["simulatable"] is False
        assert por_id["web"]["endpoint"] == "/api/v1/channels/web/messages"


# ==================================================== abertura com saudação
class TestAberturaDeConversa:
    def test_cumprimenta_pelo_nome_antes_da_primeira_mensagem(self, client, maria):
        response = client.post("/api/v1/channels/conversations",
                               json={"customer_id": maria.id, "channel": "whatsapp"})

        assert response.status_code == 200
        body = response.json()
        assert maria.first_name in body["greeting"]
        assert body["resumed"] is False
        assert body["conversation_id"]

    def test_nao_repete_a_saudacao_ao_reabrir_uma_conversa_em_andamento(self, client, maria):
        client.post("/api/v1/channels/conversations",
                    json={"customer_id": maria.id, "channel": "whatsapp"})

        again = client.post("/api/v1/channels/conversations",
                            json={"customer_id": maria.id, "channel": "app"}).json()

        assert again["resumed"] is True
        assert again["greeting"] == ""

    def test_informa_qual_versao_da_persona_produziu_o_texto(self, client, maria):
        body = client.post("/api/v1/channels/conversations",
                           json={"customer_id": maria.id, "channel": "web"}).json()

        assert body["persona_version"] >= 1
        assert body["response_source"] in {"generative", "template"}

    def test_404_para_cliente_inexistente(self, client):
        response = client.post("/api/v1/channels/conversations",
                               json={"customer_id": "cus_fantasma", "channel": "web"})
        assert response.status_code == 404


# ======================================================= continuidade entre canais
class TestContinuidadeEntreCanais:
    def test_pergunta_antes_de_presumir_ao_trocar_de_canal(self, client, maria):
        send(client, "whatsapp", "Quero mudar meu plano", maria.id)

        troca = send(client, "app", "oi", maria.id).json()

        assert troca["awaiting_context_confirmation"] is True
        assert troca["context_recovered"] is True
        assert "WhatsApp" in troca["reply"] or "whatsapp" in troca["reply"].lower()

    def test_confirmar_retoma_o_assunto_anterior(self, client, maria):
        send(client, "whatsapp", "Quero mudar meu plano", maria.id)
        send(client, "app", "oi", maria.id)

        confirmacao = send(client, "app", "sim, quero continuar", maria.id).json()

        assert confirmacao["awaiting_context_confirmation"] is False

    def test_recusar_abre_uma_conversa_nova(self, client, maria):
        primeira = send(client, "whatsapp", "Quero mudar meu plano", maria.id).json()
        send(client, "app", "oi", maria.id)

        nova = send(client, "app", "não, é outro assunto", maria.id).json()

        assert nova["conversation_id"] != primeira["conversation_id"]
        assert nova["awaiting_context_confirmation"] is False

    def test_a_memoria_e_indexada_pelo_cliente_e_nao_pelo_canal(self, client, maria):
        primeira = send(client, "whatsapp", "Quero mudar meu plano", maria.id).json()
        segunda = send(client, "app", "oi", maria.id).json()

        assert segunda["conversation_id"] == primeira["conversation_id"]


# ======================================================================= clientes
class TestClientes:
    def test_lista_as_personas_com_o_contexto_que_a_ia_vai_usar(self, client):
        clientes = client.get("/api/v1/customers").json()

        assert len(clientes) >= 5
        primeiro = clientes[0]
        assert primeiro["persona_summary"]
        assert "marketing_opt_in" in primeiro
        assert "conversation_count" in primeiro

    def test_nenhum_cliente_comeca_com_conversa(self, client):
        clientes = client.get("/api/v1/customers").json()

        assert all(c["conversation_count"] == 0 for c in clientes)
        assert all(c["open_conversation_id"] is None for c in clientes)

    def test_contexto_consolidado_mascara_o_documento(self, client, maria):
        contexto = client.get(f"/api/v1/customers/{maria.id}/context").json()

        assert contexto["name"] == maria.name
        assert "*" in contexto["document_masked"]
        assert contexto["plan"] is not None

    def test_contexto_de_cliente_inexistente_da_404(self, client):
        assert client.get("/api/v1/customers/cus_fantasma/context").status_code == 404

    def test_conversas_do_cliente_aparecem_depois_da_interacao(self, client, maria):
        antes = client.get(f"/api/v1/customers/{maria.id}/conversations").json()
        send(client, "web", "oi", maria.id)
        depois = client.get(f"/api/v1/customers/{maria.id}/conversations").json()

        assert antes == []
        assert len(depois) == 1
        assert depois[0]["customer_id"] == maria.id


# ==================================================================== console
class TestConsole:
    def test_a_fila_comeca_vazia(self, client):
        assert client.get("/api/v1/conversations").json() == []

    def test_a_conversa_simulada_entra_na_fila(self, client, maria):
        send(client, "whatsapp", "minha internet caiu", maria.id)

        fila = client.get("/api/v1/conversations").json()

        assert len(fila) == 1
        assert fila[0]["customer_name"] == maria.name
        assert fila[0]["channel"] == "whatsapp"

    def test_filtra_a_fila_por_area(self, client, maria, felipe):
        send(client, "web", "quero contratar um plano maior", maria.id)

        vendas = client.get("/api/v1/conversations?area=Vendas").json()
        financeiro = client.get("/api/v1/conversations?area=Financeiro").json()

        assert len(vendas) + len(financeiro) <= 1

    def test_filtra_a_fila_por_canal_e_por_busca(self, client, maria):
        send(client, "app", "oi", maria.id)

        assert client.get("/api/v1/conversations?channel=app").json()
        assert client.get("/api/v1/conversations?channel=whatsapp").json() == []
        assert client.get(f"/api/v1/conversations?search={maria.first_name}").json()

    def test_transcricao_traz_o_painel_de_apoio_ao_atendente(self, client, maria):
        conversa = send(client, "web", "quero mudar de plano", maria.id).json()

        detalhe = client.get(f"/api/v1/conversations/{conversa['conversation_id']}").json()

        assert len(detalhe["messages"]) >= 2
        assert detalhe["ai"]["intent"] is not None
        assert "handover" in detalhe["ai"]

    def test_conversa_inexistente_da_404(self, client):
        assert client.get("/api/v1/conversations/conv_fantasma").status_code == 404

    def test_atendente_assume_a_conversa(self, client, maria):
        conversa = send(client, "web", "quero falar com atendente", maria.id).json()
        conversa_id = conversa["conversation_id"]

        transferida = client.post(f"/api/v1/conversations/{conversa_id}/handover",
                                  json={"reason": "pedido do cliente",
                                        "agent": "Ana"}).json()

        assert transferida["status"] == "transferred"
        assert transferida["handover_requested"] is True

    def test_atendente_responde_e_a_mensagem_entra_na_transcricao(self, client, maria):
        conversa = send(client, "web", "oi", maria.id).json()
        conversa_id = conversa["conversation_id"]

        mensagem = client.post(f"/api/v1/conversations/{conversa_id}/messages",
                               json={"text": "Oi, sou a Ana. Já vi seu caso."}).json()

        assert mensagem["author"] == "agent"
        detalhe = client.get(f"/api/v1/conversations/{conversa_id}").json()
        assert any(m["author"] == "agent" for m in detalhe["messages"])

    def test_o_bot_nao_fala_por_cima_do_atendente(self, client, maria):
        conversa = send(client, "web", "quero falar com atendente", maria.id).json()
        conversa_id = conversa["conversation_id"]
        client.post(f"/api/v1/conversations/{conversa_id}/handover",
                    json={"reason": "pedido do cliente", "agent": "Ana"})

        depois = send(client, "web", "ainda estou aqui, Ana", maria.id).json()

        assert depois["conversation_id"] == conversa_id
        # O assistente não diz nada: quem está com o caso é uma pessoa.
        assert depois["reply"] == ""
        detalhe = client.get(f"/api/v1/conversations/{conversa_id}").json()
        assert detalhe["status"] == "transferred"
        assert detalhe["ai"]["handover"]["assigned_agent"] == "Ana"
        # ...mas a mensagem chegou à transcrição, à vista do atendente.
        assert any(m["text"] == "ainda estou aqui, Ana" for m in detalhe["messages"])


# =================================================================== dashboard
class TestDashboard:
    def test_comeca_sem_dado_nenhum(self, client):
        painel = client.get("/api/v1/dashboard").json()

        assert painel["has_data"] is False
        assert painel["conversations"]["value"] == 0
        assert painel["channels"] == [] or all(c["value"] == 0 for c in painel["channels"])

    def test_a_primeira_conversa_move_o_numero(self, client, maria):
        send(client, "whatsapp", "oi", maria.id)

        painel = client.get("/api/v1/dashboard").json()

        assert painel["has_data"] is True
        assert painel["conversations"]["value"] == 1

    def test_metricas_por_area(self, client, maria):
        send(client, "web", "quero mudar de plano", maria.id)

        painel = client.get("/api/v1/dashboard?area=Vendas").json()

        assert painel["area"] == "Vendas"

    def test_distribuicao_por_canal_reflete_o_canal_usado(self, client, maria):
        send(client, "app", "oi", maria.id)

        painel = client.get("/api/v1/dashboard").json()
        usados = {c["name"]: c["value"] for c in painel["channels"] if c["value"]}

        assert "App Claro" in usados or "App" in " ".join(usados)


# ============================================================== design studio
class TestDesignStudio:
    def test_devolve_a_configuracao_vigente_com_versao(self, client):
        config = client.get("/api/v1/studio/config").json()

        assert config["persona"]["name"]
        assert config["version"] >= 1
        assert len(config["channels"]) == 4

    def test_salvar_incrementa_a_versao(self, client):
        antes = client.get("/api/v1/studio/config").json()

        depois = client.put("/api/v1/studio/config", json={
            **antes,
            "persona": {**antes["persona"], "name": "Clarice"},
        }).json()

        assert depois["persona"]["name"] == "Clarice"
        assert depois["version"] == antes["version"] + 1

    def test_ajustar_um_canal_nao_mexe_nos_outros(self, client):
        client.patch("/api/v1/studio/channels/whatsapp", json={"useEmoji": False})

        config = client.get("/api/v1/studio/config").json()
        por_id = {c["id"]: c for c in config["channels"]}

        assert por_id["whatsapp"]["useEmoji"] is False
        assert por_id["webchat"]["useEmoji"] is not None

    def test_canal_inexistente_da_404(self, client):
        assert client.patch("/api/v1/studio/channels/pombo",
                            json={"useEmoji": False}).status_code == 404

    def test_previa_mostra_a_mesma_frase_em_cada_canal(self, client):
        previa = client.post("/api/v1/studio/preview",
                             json={"message": "Seu plano foi alterado com sucesso."}).json()

        assert previa["persona_name"]
        assert len(previa["previews"]) >= 3
        for canal in previa["previews"]:
            assert canal["rendered"]
            assert canal["length"] == len(canal["rendered"])

    def test_a_previa_muda_quando_a_configuracao_muda(self, client):
        com_emoji = client.post("/api/v1/studio/preview",
                                json={"message": "Tudo certo! 🎉",
                                      "channels": ["whatsapp"]}).json()
        client.patch("/api/v1/studio/channels/whatsapp", json={"useEmoji": False})
        sem_emoji = client.post("/api/v1/studio/preview",
                                json={"message": "Tudo certo! 🎉",
                                      "channels": ["whatsapp"]}).json()

        assert "🎉" in com_emoji["previews"][0]["rendered"]
        assert "🎉" not in sem_emoji["previews"][0]["rendered"]

    def test_a_mudanca_de_persona_vale_na_proxima_mensagem(self, client, maria):
        antes = send(client, "whatsapp", "oi", maria.id).json()
        client.patch("/api/v1/studio/channels/whatsapp", json={"useEmoji": False})

        depois = send(client, "whatsapp", "e aí", maria.id).json()

        assert depois["persona_version"] > antes["persona_version"]


# ============================================================== contato ativo
class TestContatoAtivo:
    def test_indica_quem_procurar_com_motivo_explicito(self, client):
        elegiveis = client.get("/api/v1/outreach/eligible").json()

        assert elegiveis
        contactavel = next(c for c in elegiveis if c["can_contact"])
        assert contactavel["reasons"]
        assert contactavel["suggested_offer"] is not None
        assert contactavel["score"] > 0

    def test_ordena_por_afinidade(self, client):
        elegiveis = client.get("/api/v1/outreach/eligible").json()
        scores = [c["score"] for c in elegiveis]

        assert scores == sorted(scores, reverse=True)

    def test_expoe_o_impedimento_de_quem_nao_pode_ser_abordado(self, client, felipe):
        elegiveis = client.get("/api/v1/outreach/eligible").json()

        bloqueado = next(c for c in elegiveis if c["customer_id"] == felipe.id)
        assert bloqueado["can_contact"] is False
        assert bloqueado["blocks"]
        assert bloqueado["marketing_opt_in"] is False

    def test_filtra_apenas_os_contactaveis(self, client):
        todos = client.get("/api/v1/outreach/eligible").json()
        so_contactaveis = client.get("/api/v1/outreach/eligible?only_contactable=true").json()

        assert len(so_contactaveis) < len(todos)
        assert all(c["can_contact"] for c in so_contactaveis)

    def test_abordagem_cria_uma_conversa_iniciada_pela_claro(self, client):
        elegivel = next(c for c in client.get("/api/v1/outreach/eligible").json()
                        if c["can_contact"])

        resultado = client.post("/api/v1/outreach/send", json={
            "customer_id": elegivel["customer_id"],
            "offer_id": elegivel["suggested_offer"]["id"],
        }).json()

        assert resultado["message"]
        conversa = client.get(f"/api/v1/conversations/{resultado['conversation_id']}")
        assert conversa.status_code == 200
        fila = client.get("/api/v1/conversations").json()
        assert fila[0]["initiated_by_company"] is True

    def test_recusa_a_abordagem_sem_consentimento(self, client, felipe):
        elegiveis = client.get("/api/v1/outreach/eligible").json()
        bloqueado = next(c for c in elegiveis if c["customer_id"] == felipe.id)

        response = client.post("/api/v1/outreach/send", json={
            "customer_id": felipe.id,
            "offer_id": (bloqueado["suggested_offer"] or {}).get("id", "qualquer"),
        })

        assert response.status_code == 403
        assert "não autorizou" in response.json()["detail"].lower()

    def test_fora_da_janela_de_24h_exige_modelo_aprovado(self, client):
        elegiveis = client.get("/api/v1/outreach/eligible").json()

        fechados = [c for c in elegiveis if not c["window_open"]]
        assert fechados, "o cenário precisa de ao menos um cliente fora da janela"
        assert all(c["requires_template"] for c in fechados)

    def test_cliente_inexistente_da_404(self, client):
        response = client.post("/api/v1/outreach/send",
                               json={"customer_id": "cus_fantasma", "offer_id": "x"})
        assert response.status_code == 404


# ==================================================================== operação
class TestOperacao:
    def test_health_reporta_o_modo_de_cada_componente(self, client):
        health = client.get("/health").json()

        assert health["status"] in {"ok", "degraded"}
        componentes = health["components"]
        assert componentes["intent_engine"]
        assert componentes["response_generator"]
        assert isinstance(componentes["generative_ai"], bool)

    def test_auditoria_registra_o_acesso_a_dado_de_cliente(self, client, maria):
        client.get(f"/api/v1/customers/{maria.id}/context")

        trilha = client.get(f"/api/v1/audit?customer_id={maria.id}").json()

        assert trilha
        assert all(e["customer_id"] == maria.id for e in trilha)

    def test_a_raiz_leva_a_documentacao(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code in {307, 302}
        assert "docs" in response.headers["location"]

    def test_a_especificacao_openapi_esta_publicada(self, client):
        spec = client.get("/openapi.json").json()

        assert spec["info"]["title"]
        tags = {t["name"] for t in spec["tags"]}
        assert "Ingestão de Canais" in tags
        assert "Console · Contato Ativo" in tags

    def test_a_especificacao_nao_menciona_numeracao_de_requisito(self, client):
        texto = client.get("/openapi.json").text

        assert "RF00" not in texto
        assert "RNF0" not in texto


# ============================================================ canal WhatsApp
class TestCanalWhatsApp:
    def test_status_nunca_devolve_credencial(self, client):
        status = client.get("/api/v1/channels/whatsapp/status").json()

        assert status["access_token"] in {"configurado", "ausente"}
        assert status["verify_token"] in {"configurado", "ausente"}
        assert "EAA" not in str(status)

    def test_status_lista_o_que_falta_configurar(self, client):
        status = client.get("/api/v1/channels/whatsapp/status").json()

        assert isinstance(status["missing"], list)
        assert status["webhook_url"].endswith("/webhook")

    def test_handshake_recusa_token_errado(self, client):
        response = client.get("/api/v1/channels/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "123",
        })
        assert response.status_code == 403

    def test_envio_bloqueado_enquanto_o_canal_esta_desligado(self, client):
        response = client.post("/api/v1/channels/whatsapp/send",
                               json={"to": "+5511999990001", "text": "oi"})
        assert response.status_code == 503


# ====================================================== regressões de conversa
class TestRegressoesDeConversa:
    """Defeitos encontrados rodando a demonstração, com teste para não voltarem."""

    def test_nao_desiste_do_cliente_na_primeira_mensagem_mal_entendida(self, client, maria):
        """Escalar no primeiro tropeço faria do hub um encaminhador de fila."""
        primeira = send(client, "web", "xyzzy plugh", maria.id).json()

        assert primeira["handover_triggered"] is False
        assert primeira["reply"]

    def test_escala_quando_a_incompreensao_se_repete(self, client, maria):
        for _ in range(3):
            ultima = send(client, "web", "xyzzy plugh", maria.id).json()

        assert ultima["handover_triggered"] is True

    def test_entende_o_cliente_pedindo_mais_internet_sem_dizer_plano(self, client, maria):
        """As sugestões que a própria tela oferece precisam funcionar."""
        for frase in ("Quero aumentar minha franquia de internet",
                      "Quanto ficaria um plano com mais dados?"):
            body = send(client, "web", frase, maria.id).json()
            assert body["intent"]["slug"] == "alteracao_plano", frase
            assert body["flow"] == "venda", frase

    def test_nao_repete_a_mesma_frase_duas_vezes_seguidas(self, client, maria):
        send(client, "whatsapp", "Quero aumentar minha franquia", maria.id)
        send(client, "app", "oi", maria.id)

        retomada = send(client, "app", "sim, quero continuar nesse assunto", maria.id).json()

        detalhe = client.get(f"/api/v1/conversations/{retomada['conversation_id']}").json()
        falas = [m["text"] for m in detalhe["messages"] if m["author"] == "bot"]
        assert len(falas) == len(set(falas)), "o assistente repetiu uma fala palavra por palavra"

    def test_a_retomada_mantem_o_assunto_e_os_sistemas_consultados(self, client, maria):
        send(client, "whatsapp", "Quero aumentar minha franquia", maria.id)
        send(client, "app", "oi", maria.id)

        retomada = send(client, "app", "sim, quero continuar nesse assunto", maria.id).json()

        assert retomada["intent"]["slug"] == "alteracao_plano"
        assert retomada["flow"] == "venda"
        assert "catalogo_planos" in retomada["services_consulted"]


# ==================================================== silêncio após transbordo
class TestSilencioAposTransbordo:
    """Depois do transbordo, quem fala é a pessoa.

    O assistente não responde, não confirma recebimento e não diz "já já alguém
    te atende": um robô comentando por cima do atendente é ruído para os dois
    lados da conversa.
    """

    def _transferir(self, client, maria) -> str:
        conversa = send(client, "web", "quero falar com atendente", maria.id).json()
        conversa_id = conversa["conversation_id"]
        client.post(f"/api/v1/conversations/{conversa_id}/handover",
                    json={"reason": "pedido do cliente", "agent": "Ana"})
        return conversa_id

    def test_o_assistente_nao_responde_mais_nada(self, client, maria):
        conversa_id = self._transferir(client, maria)

        for texto in ("tudo bem?", "consegue ver meu caso?", "alô?"):
            resposta = send(client, "web", texto, maria.id).json()
            assert resposta["reply"] == "", texto
            assert resposta["conversation_id"] == conversa_id

    def test_as_mensagens_continuam_chegando_ao_atendente(self, client, maria):
        conversa_id = self._transferir(client, maria)
        send(client, "web", "consegue ver meu caso?", maria.id)

        detalhe = client.get(f"/api/v1/conversations/{conversa_id}").json()

        textos = [m["text"] for m in detalhe["messages"]]
        assert "consegue ver meu caso?" in textos
        # nenhuma fala do bot depois da transferência
        indice = textos.index("consegue ver meu caso?")
        assert all(m["author"] != "bot" for m in detalhe["messages"][indice:])

    def test_a_conversa_sobe_na_fila(self, client, maria):
        conversa_id = self._transferir(client, maria)
        send(client, "web", "alguém?", maria.id)

        fila = client.get("/api/v1/conversations").json()
        atual = next(c for c in fila if c["id"] == conversa_id)
        assert atual["priority"] == "high"

    def test_o_atendente_responde_e_a_resposta_chega(self, client, maria):
        conversa_id = self._transferir(client, maria)

        client.post(f"/api/v1/conversations/{conversa_id}/messages",
                    json={"text": "Oi, sou a Ana. Já estou com o seu caso."})

        detalhe = client.get(f"/api/v1/conversations/{conversa_id}").json()
        assert detalhe["messages"][-1]["author"] == "agent"


# ================================================ pesquisa de satisfação (NPS)
class TestPesquisaDeSatisfacao:
    def test_a_despedida_do_cliente_encerra_e_dispara_a_pesquisa(self, client, maria):
        send(client, "whatsapp", "quero aumentar minha franquia", maria.id)

        fim = send(client, "whatsapp", "obrigada, era só isso", maria.id).json()

        assert fim["awaiting_nps"] is True
        assert fim["conversation_closed"] is True
        assert "0 a 10" in fim["reply"]

    def test_o_atendente_encerrando_dispara_a_mesma_pesquisa(self, client, maria):
        conversa = send(client, "web", "quero falar com atendente", maria.id).json()
        conversa_id = conversa["conversation_id"]

        encerrada = client.post(f"/api/v1/conversations/{conversa_id}/close",
                                json={"agent": "Ana Ribeiro"}).json()

        assert encerrada["survey_sent"] is True
        assert "0 a 10" in encerrada["survey_message"]
        assert encerrada["conversation"]["closed_by"] == "Ana Ribeiro"

    def test_a_nota_do_cliente_e_registrada_com_a_categoria(self, client, maria):
        send(client, "whatsapp", "quero aumentar minha franquia", maria.id)
        send(client, "whatsapp", "obrigada, era só isso", maria.id)

        resposta = send(client, "whatsapp", "9", maria.id).json()

        assert resposta["nps_score"] == 9
        assert resposta["awaiting_nps"] is False
        fila = client.get("/api/v1/conversations").json()
        assert fila[0]["nps_category"] == "promotor"

    def test_reconhece_a_nota_escrita_por_extenso_ou_com_texto(self, client, maria, felipe):
        for cliente, texto, esperado in ((maria, "nota 10", 10), (felipe, "daria uns 4", 4)):
            send(client, "web", "quero mudar de plano", cliente.id)
            send(client, "web", "valeu, era só isso", cliente.id)

            resposta = send(client, "web", texto, cliente.id).json()

            assert resposta["nps_score"] == esperado, texto

    def test_a_resposta_muda_conforme_a_nota(self, client, maria, felipe):
        def encerrar_e_avaliar(cliente, nota):
            send(client, "web", "quero mudar de plano", cliente.id)
            send(client, "web", "obrigado, resolvido", cliente.id)
            return send(client, "web", str(nota), cliente.id).json()["reply"]

        detrator = encerrar_e_avaliar(maria, 3)
        promotor = encerrar_e_avaliar(felipe, 10)

        assert detrator != promotor
        assert "devendo" in detrator.lower()

    def test_insiste_uma_vez_e_desiste_com_elegancia(self, client, maria):
        send(client, "web", "quero mudar de plano", maria.id)
        send(client, "web", "obrigada, era só isso", maria.id)

        primeira = send(client, "web", "sei lá", maria.id).json()
        segunda = send(client, "web", "sei lá de novo", maria.id).json()

        assert primeira["awaiting_nps"] is True
        assert "0 a 10" in primeira["reply"]
        assert segunda["awaiting_nps"] is False, "insistir duas vezes vira cobrança"

    def test_quem_recusa_e_encerrado_sem_insistencia(self, client, maria):
        send(client, "web", "quero mudar de plano", maria.id)
        send(client, "web", "obrigada, era só isso", maria.id)

        recusa = send(client, "web", "não quero responder", maria.id).json()

        assert recusa["awaiting_nps"] is False
        assert recusa["nps_score"] is None

    def test_uma_despedida_educada_no_meio_do_pedido_nao_encerra(self, client, maria):
        resposta = send(client, "web",
                        "Obrigada por me mostrar as opções, mas antes quero saber "
                        "quanto fica o plano de 50GB", maria.id).json()

        assert resposta["conversation_closed"] is False
        assert resposta["awaiting_nps"] is False

    def test_a_nota_alimenta_o_nps_do_painel(self, client, maria):
        send(client, "web", "quero mudar de plano", maria.id)
        send(client, "web", "obrigada, era só isso", maria.id)
        send(client, "web", "10", maria.id)

        painel = client.get("/api/v1/dashboard").json()

        assert painel["nps"]["value"] == 100

    def test_encerrar_conversa_inexistente_da_404(self, client):
        assert client.post("/api/v1/conversations/conv_fantasma/close",
                           json={"agent": "Ana"}).status_code == 404


# ============================================ agrupamento pela janela de espera
class TestJanelaDeEspera:
    """A janela vive no roteador, entre o transporte e o caso de uso.

    A suíte roda com janela zero — o agrupamento em si é verificado em
    `test_debounce.py`. Aqui só se confirma que o contrato HTTP diz a verdade
    sobre o que aconteceu.
    """

    def test_com_janela_zero_a_resposta_sai_na_hora(self, client, maria):
        resposta = send(client, "web", "quero mudar de plano", maria.id).json()

        assert resposta["superseded"] is False
        assert resposta["reply"]

    def test_a_mensagem_absorvida_e_declarada_no_contrato(self, client, container, maria):
        """Uma mensagem agrupada não é erro nem resposta vazia sem explicação:
        o campo `superseded` diz que o hub está esperando o cliente terminar."""
        from app.infrastructure.buffering.message_debouncer import MessageDebouncer

        class SempreAgrupa(MessageDebouncer):
            async def submit(self, key: str, text: str) -> str | None:
                return None

        container.debouncer = SempreAgrupa(0)

        resposta = send(client, "web", "oi, tudo bem?", maria.id).json()

        assert resposta["superseded"] is True
        assert resposta["reply"] == ""
        assert resposta["flow"] == "agrupada"
        assert client.get("/api/v1/conversations").json() == [], \
            "mensagem agrupada não abre conversa sozinha"

    def test_encerrar_descarta_o_lote_em_espera(self, client, container, maria):
        conversa = send(client, "web", "quero mudar de plano", maria.id).json()
        descartados: list[str] = []
        original = container.debouncer.flush

        async def espiao(key: str) -> None:
            descartados.append(key)
            await original(key)

        container.debouncer.flush = espiao

        client.post(f"/api/v1/conversations/{conversa['conversation_id']}/close",
                    json={"agent": "Ana"})

        assert descartados == [maria.id]
