"""Persona da marca — quem é o assistente da Claro."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Persona(BaseModel):
    name: str = "Clara"
    description: str = ""
    traits: list[str] = Field(default_factory=list)
