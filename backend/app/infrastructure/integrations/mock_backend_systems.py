"""Adaptador dos sistemas internos da Claro.

Cada metodo representa uma integracao que, em producao, seria uma chamada ao
sistema real (BSS, billing, OSS, CRM). Os contratos de retorno sao realistas de
proposito: substituir o mock pela integracao verdadeira e reescrever o corpo de
um metodo, sem tocar em caso de uso nem no dominio.

A latencia artificial existe para que a interface seja construida contra um
sistema que demora -- e nao contra um que responde instantaneamente e esconde
os estados de carregamento.
"""
from __future__ import annotations

import asyncio
import random

from ...domain.ports import BackendSystems

CATALOG: dict[str, dict] = {
    "Claro Flex 20GB": {"price": 59.90, "data_gb": 20},
    "Claro Flex 30GB": {"price": 79.90, "data_gb": 30},
    "Claro Flex 50GB": {"price": 99.90, "data_gb": 50},
    "Claro Flex 60GB": {"price": 109.90, "data_gb": 60},
    "Combo Família": {"price": 189.90, "data_gb": 120},
}


class MockBackendSystems(BackendSystems):
    def __init__(self, simulate_latency: bool = True) -> None:
        self._latency = simulate_latency

    @property
    def available(self) -> list[str]:
        return ["catalogo_planos", "faturamento", "diagnostico_tecnico", "crm"]

    async def call(self, service: str, **kwargs) -> dict:
        if service not in self.available:
            raise ValueError(f"Serviço interno desconhecido: {service}")
        await self._wait()
        return await getattr(self, f"_{service}")(**kwargs)

    async def _wait(self, lo: float = 0.02, hi: float = 0.09) -> None:
        if self._latency:
            await asyncio.sleep(random.uniform(lo, hi))

    # -- integracoes simuladas -------------------------------------------
    async def _catalogo_planos(self, current_plan: str | None = None, **_) -> dict:
        """Sistema real: BSS de produtos e ofertas."""
        current_gb = CATALOG.get(current_plan or "", {}).get("data_gb", 0)
        upgrades = [
            {"name": name, "price": spec["price"], "data_gb": spec["data_gb"]}
            for name, spec in CATALOG.items() if spec["data_gb"] > current_gb
        ]
        return {
            "service": "catalogo_planos",
            "current": current_plan,
            "upgrades": sorted(upgrades, key=lambda p: p["data_gb"])[:3],
        }

    async def _faturamento(self, customer_id: str = "", **_) -> dict:
        """Sistema real: plataforma de billing."""
        return {
            "service": "faturamento",
            "customer_id": customer_id,
            "status": "em dia",
            "due_day": 10,
            "last_invoice": {"reference": "07/2026", "amount": 79.90, "paid": True},
            "second_copy_url": f"https://minhaclaro.example/faturas/{customer_id}/atual.pdf",
        }

    async def _diagnostico_tecnico(self, customer_id: str = "", **_) -> dict:
        """Sistema real: OSS / plataforma de rede."""
        return {
            "service": "diagnostico_tecnico",
            "customer_id": customer_id,
            "signal": "estável",
            "incidents_nearby": 0,
            "last_check": "agora",
            "recommendation": "Nenhuma instabilidade detectada na região do cliente.",
        }

    async def _crm(self, customer_id: str = "", **_) -> dict:
        """Sistema real: CRM e segmentação."""
        return {
            "service": "crm",
            "customer_id": customer_id,
            "segment": "VIP",
            "customer_since": "Janeiro 2023",
            "churn_risk": 0.12,
        }
