"""Área de negócio responsável por um atendimento."""
from __future__ import annotations

from enum import Enum


class Area(str, Enum):
    suporte = "Suporte"
    vendas = "Vendas"
    financeiro = "Financeiro"
    marketing = "Marketing"
    retencao = "Retenção"
    tecnico = "Técnico"
