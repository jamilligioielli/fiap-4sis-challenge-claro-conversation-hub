"""Servico de dominio: composicao da resposta de negocio.

Produz o conteudo da resposta a partir do fluxo e dos dados que vieram dos
sistemas internos. O texto que sai daqui ainda esta "cru": quem veste com o tom
de voz e o PersonaService.

Separar as duas coisas permite mudar a regra de negocio sem mexer no tom, e o
tom sem mexer na regra.
"""
from __future__ import annotations

import re
import unicodedata

from ..value_objects import Intent
from .routing_service import Flow

AFFIRMATIONS = (
    "sim", "pode prosseguir", "pode seguir", "confirmo", "confirmar", "quero sim",
    "isso mesmo", "ok", "beleza", "fechado", "vamos", "aceito", "prossegue",
)


def _is_affirmation(text: str) -> bool:
    """Detecta confirmação do cliente.

    Sem isto o bot reapresenta a mesma oferta a cada turno — que é a versão
    conversacional de não ouvir o cliente.

    A comparação é por palavra inteira: "assim" contém "sim", e tratar
    "meu plano assim não serve" como confirmação registraria uma alteração que
    o cliente não pediu.
    """
    nfkd = unicodedata.normalize("NFKD", text.lower().strip(" .!?"))
    normalized = "".join(c for c in nfkd if not unicodedata.combining(c))
    return any(re.search(rf"\b{re.escape(a)}\b", normalized) for a in AFFIRMATIONS)


def brl(value: float) -> str:
    return f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


class ReplyComposer:
    def compose(self, flow: Flow, intent: Intent, data: dict,
                current_plan: str | None = None, text: str = "") -> str:
        handler = getattr(self, f"_{flow.value}", self._fallback)
        return handler(intent, data, current_plan, text)

    # -- fluxos -----------------------------------------------------------
    def _venda(self, intent: Intent, data: dict, current_plan: str | None,
               text: str = "") -> str:
        upgrades = data.get("catalogo_planos", {}).get("upgrades", [])
        wanted = intent.entities.get("plano")

        # Cliente confirmando uma oferta já apresentada: avança, não repete.
        if wanted and _is_affirmation(text):
            return (f"Perfeito! Estou registrando a alteração para o {wanted}. "
                    f"A mudança entra em vigor no seu próximo ciclo de faturamento e "
                    f"você recebe a confirmação por mensagem. Posso ajudar em algo mais?")

        if wanted:
            match = next((u for u in upgrades if u["name"].lower() == wanted.lower()), None)
            if match:
                return (f"Continuamos sua solicitação por aqui. O plano {match['name']} custa "
                        f"R$ {brl(match['price'])}/mês. Posso prosseguir com a alteração?")
            return (f"Anotei seu interesse no {wanted}. Vou confirmar a disponibilidade para "
                    f"a sua linha e já te retorno.")

        if upgrades:
            options = ", ".join(f"{u['name']} (R$ {brl(u['price'])})" for u in upgrades[:2])
            base = f" Hoje você está no {current_plan}." if current_plan else ""
            return (f"Posso te ajudar com a alteração do seu plano.{base} As opções "
                    f"disponíveis para você são: {options}. Qual delas faz sentido?")

        return "Posso te ajudar com a alteração do seu plano. Qual plano você gostaria de contratar?"

    def _financeiro(self, intent: Intent, data: dict, _plan, text: str = "") -> str:
        fat = data.get("faturamento", {})
        last = fat.get("last_invoice", {})
        situation = "está em dia" if fat.get("status") == "em dia" else "consta em aberto"
        return (f"Sua fatura {situation}. A última referência é {last.get('reference', '—')}, "
                f"no valor de R$ {brl(last.get('amount', 0))}, com vencimento todo dia "
                f"{fat.get('due_day', 10)}. Quer que eu envie a segunda via?")

    def _suporte(self, intent: Intent, data: dict, _plan, text: str = "") -> str:
        diag = data.get("diagnostico_tecnico", {})
        return (f"Já verifiquei sua conexão: o sinal está {diag.get('signal', 'em análise')} e "
                f"não há incidentes na sua região. {diag.get('recommendation', '')} "
                f"Vamos tentar reiniciar o roteador e ver se melhora?")

    def _retencao(self, intent: Intent, data: dict, _plan, text: str = "") -> str:
        upgrades = data.get("catalogo_planos", {}).get("upgrades", [])
        offer = f" Antes disso, posso te mostrar o {upgrades[0]['name']}?" if upgrades else ""
        return ("Entendo, e lamento que você esteja pensando em sair. Quero entender o que não "
                f"está funcionando para ver o que consigo fazer por você.{offer}")

    def _informacao(self, intent: Intent, data: dict, _plan, text: str = "") -> str:
        upgrades = data.get("catalogo_planos", {}).get("upgrades", [])
        if upgrades:
            listing = ", ".join(f"{u['name']} por R$ {brl(u['price'])}" for u in upgrades[:3])
            return f"Claro! As opções disponíveis são: {listing}. Quer detalhes de alguma?"
        return "Claro! Me conta o que você quer saber que eu te explico."

    def _handover(self, *_args, **_kw) -> str:
        return ("Sem problema, vou te transferir para um de nossos atendentes agora. Ele já "
                "recebe todo o histórico da conversa, então você não precisa repetir nada.")

    def _fallback(self, *_args, **_kw) -> str:
        return ("Não tenho certeza de que entendi. Você quer falar sobre plano, fatura, "
                "suporte técnico ou outro assunto?")
