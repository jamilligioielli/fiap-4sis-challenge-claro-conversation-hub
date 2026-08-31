"""Intenção mapeada no Design Studio."""
from __future__ import annotations

from pydantic import BaseModel


class ConfiguredIntent(BaseModel):
    """`examples` alimenta o prompt do classificador — mapear uma intenção nova
    na interface muda o comportamento do modelo sem implantação."""

    slug: str
    name: str
    confidence: str = "Alta"
    examples: str = ""
