"""Contato ativo — quando a Claro inicia a conversa."""
from __future__ import annotations

from .contact_window import ContactWindow
from .eligibility import EligibilityReason, EligibleCustomer, OutreachBlock
from .offer import Offer
from .template_category import TemplateCategory

__all__ = [
    "ContactWindow", "EligibilityReason", "EligibleCustomer", "Offer",
    "OutreachBlock", "TemplateCategory",
]
