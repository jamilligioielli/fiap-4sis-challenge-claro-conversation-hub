"""Estado de cada componente do sistema."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    session_store: str = Field(description="`ok`, `down` ou `memory (fallback)`.")
    history_store: str
    intent_engine: str = Field(description="Classificador ativo e o seu reserva.")
    response_generator: str = Field(description="Redator ativo da resposta ao cliente.")
    generative_ai: bool = Field(
        description="Verdadeiro quando há um modelo de linguagem configurado e redigindo "
                    "as respostas. Falso significa respostas por modelo de texto.")
    backend_systems: list[str]
