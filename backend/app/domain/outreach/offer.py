"""Oferta que a Claro pode levar ativamente a um cliente."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .template_category import TemplateCategory


class Offer(BaseModel):
    id: str
    title: str
    pitch: str = Field(description="O que dizer ao cliente, em uma frase.")
    category: TemplateCategory = TemplateCategory.marketing
    plan_name: str | None = None
    price: float | None = None
    saving_hint: str = ""
