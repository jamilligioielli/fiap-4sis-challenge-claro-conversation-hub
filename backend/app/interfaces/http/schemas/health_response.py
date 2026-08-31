"""Saúde do serviço."""
from __future__ import annotations

from pydantic import BaseModel

from .component_health import ComponentHealth


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    components: ComponentHealth
