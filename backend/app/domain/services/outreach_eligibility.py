"""Quem a Claro pode abordar, por quê, e o que impede.

Contato ativo é onde uma operadora ganha ou destrói confiança. Por isso a regra
mora no domínio, com o motivo sempre explícito: o gestor vê por que aquele
cliente apareceu na lista antes de decidir falar com ele.
"""
from __future__ import annotations

from ..entities.customer import Customer
from ..outreach.contact_window import ContactWindow
from ..outreach.eligibility import EligibilityReason, EligibleCustomer, OutreachBlock
from ..outreach.offer import Offer
from ..outreach.template_category import TemplateCategory

CATALOG = {
    "Claro Flex 20GB": {"price": 59.90, "data_gb": 20},
    "Claro Flex 30GB": {"price": 79.90, "data_gb": 30},
    "Claro Flex 50GB": {"price": 99.90, "data_gb": 50},
    "Claro Flex 60GB": {"price": 109.90, "data_gb": 60},
    "Combo Família": {"price": 189.90, "data_gb": 120},
}

HIGH_USAGE = 80
MEDIUM_USAGE = 60


class OutreachEligibilityService:
    def evaluate(self, customer: Customer) -> EligibleCustomer:
        reasons = self._reasons(customer)
        offer = self._offer(customer, reasons)
        window = ContactWindow(customer.last_inbound_at)
        blocks = self._blocks(customer, offer, reasons)

        return EligibleCustomer(
            customer_id=customer.id,
            customer_name=customer.name,
            segment=customer.segment,
            reasons=reasons,
            blocks=blocks,
            suggested_offer=offer,
            window_open=window.is_open,
            window_hours_remaining=window.hours_remaining,
            marketing_opt_in=customer.marketing_opt_in,
        )

    # ------------------------------------------------------------- motivos
    @staticmethod
    def _reasons(customer: Customer) -> list[EligibilityReason]:
        reasons: list[EligibilityReason] = []
        plan = customer.plan

        if plan and plan.usage_percent >= HIGH_USAGE:
            reasons.append(EligibilityReason(
                code="franquia_alta",
                description=f"Usa {plan.usage_percent}% da franquia de {plan.data_gb}GB — "
                            f"provável estouro no próximo ciclo",
                weight=0.45,
            ))
        elif plan and plan.usage_percent >= MEDIUM_USAGE:
            reasons.append(EligibilityReason(
                code="franquia_media",
                description=f"Usa {plan.usage_percent}% da franquia",
                weight=0.2,
            ))

        if customer.churn_risk < 0.25:
            reasons.append(EligibilityReason(
                code="baixo_risco",
                description=f"Risco de saída baixo ({customer.churn_risk:.0%}) — "
                            f"cliente estável, receptivo a proposta",
                weight=0.25,
            ))

        if customer.segment.upper() == "VIP":
            reasons.append(EligibilityReason(
                code="segmento_vip",
                description="Cliente VIP: prioridade de relacionamento",
                weight=0.2,
            ))

        if len(customer.products) >= 3:
            reasons.append(EligibilityReason(
                code="multiproduto",
                description=f"{len(customer.products)} produtos ativos — "
                            f"maior tolerância a nova oferta",
                weight=0.15,
            ))

        return reasons

    # ------------------------------------------------------------- bloqueios
    @staticmethod
    def _blocks(customer: Customer, offer: Offer | None,
                reasons: list[EligibilityReason]) -> list[OutreachBlock]:
        blocks: list[OutreachBlock] = []

        if not customer.marketing_opt_in:
            blocks.append(OutreachBlock(
                code="sem_opt_in",
                description="Cliente não autorizou contato com oferta. "
                            "Abordagem comercial não pode sair.",
            ))

        if customer.churn_risk >= 0.6:
            blocks.append(OutreachBlock(
                code="risco_alto",
                description=f"Risco de saída alto ({customer.churn_risk:.0%}). "
                            f"Oferta antes de resolver a insatisfação piora o quadro.",
            ))

        if offer is None:
            blocks.append(OutreachBlock(
                code="sem_oferta",
                description="Nenhuma oferta faz sentido para o plano atual deste cliente.",
            ))

        if not reasons:
            blocks.append(OutreachBlock(
                code="sem_motivo",
                description="Nada no comportamento do cliente justifica a abordagem.",
            ))

        return blocks

    # ---------------------------------------------------------------- oferta
    @staticmethod
    def _offer(customer: Customer, reasons: list[EligibilityReason]) -> Offer | None:
        plan = customer.plan
        if plan is None:
            return None

        current_gb = plan.data_gb
        upgrades = sorted(
            ((name, spec) for name, spec in CATALOG.items() if spec["data_gb"] > current_gb),
            key=lambda item: item[1]["data_gb"],
        )
        if not upgrades:
            return None

        name, spec = upgrades[0]
        extra = spec["data_gb"] - current_gb
        difference = spec["price"] - plan.price

        return Offer(
            id=f"upgrade_{name.lower().replace(' ', '_')}",
            title=name,
            pitch=(f"Mais {extra}GB por R$ {difference:.2f} a mais por mês"
                   .replace(".", ",")),
            category=TemplateCategory.marketing,
            plan_name=name,
            price=spec["price"],
            saving_hint=(f"Evita a cobrança por excedente que costuma vir quando a "
                         f"franquia estoura") if plan.usage_percent >= HIGH_USAGE else "",
        )
