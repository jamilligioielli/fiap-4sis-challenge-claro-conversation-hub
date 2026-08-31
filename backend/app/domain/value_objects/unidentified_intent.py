"""Intenção usada quando nada da taxonomia corresponde à mensagem."""
from __future__ import annotations

from .area import Area
from .intent import Intent

UNIDENTIFIED = Intent(
    slug="nao_identificada",
    name="Não Identificada",
    confidence=0.25,
    area=Area.suporte,
    reasoning="Nenhuma intenção da taxonomia correspondeu à mensagem.",
)
