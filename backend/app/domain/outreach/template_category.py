"""Categoria de modelo de mensagem para contato ativo.

A classificação segue a política do WhatsApp Business: fora da janela de
atendimento, a empresa só pode iniciar conversa por um modelo previamente
aprovado, e a categoria determina o que aquele modelo pode dizer.
"""
from __future__ import annotations

from enum import Enum


class TemplateCategory(str, Enum):
    utility = "utility"
    marketing = "marketing"
    authentication = "authentication"

    @property
    def label(self) -> str:
        return {
            "utility": "Utilidade",
            "marketing": "Marketing",
            "authentication": "Autenticação",
        }[self.value]

    @property
    def description(self) -> str:
        return {
            "utility": "Confirmações, lembretes e avisos sobre algo que o cliente já contratou.",
            "marketing": "Ofertas e promoções. Exige consentimento explícito para marketing.",
            "authentication": "Códigos de verificação e uso único.",
        }[self.value]

    @property
    def requires_marketing_consent(self) -> bool:
        return self is TemplateCategory.marketing
