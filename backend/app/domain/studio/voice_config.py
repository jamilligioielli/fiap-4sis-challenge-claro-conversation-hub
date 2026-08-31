"""Configuração da URA (canal de voz)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class VoiceConfig(BaseModel):
    """Só o canal de voz possui. A existência deste bloco é a evidência prática
    de que um canal de natureza completamente diferente foi acrescentado sem que
    o núcleo conversacional precisasse mudar."""

    speechRate: int = Field(default=50, ge=0, le=100)
    voiceGender: Literal["feminino", "masculino"] = "feminino"
    vocabularyLevel: int = Field(default=40, ge=0, le=100)
    captureMode: Literal["dtmf", "voice", "hybrid"] = "hybrid"
    menuPattern: Literal["option-key", "key-option"] = "option-key"
    maxMenuOptions: int = Field(default=5, ge=2, le=9)
    autoRepeatTimeout: int = Field(default=8, ge=0, le=30, description="segundos de silêncio")
    maxAttempts: int = Field(default=3, ge=1, le=5)
    silenceTimeout: int = Field(default=3000, ge=500, le=10000, description="milissegundos")
    transferTriggers: list[str] = Field(default_factory=list)
    queueMessage: str = ""
    scriptOpening: str = ""
    scriptMenu: str = ""
    scriptFarewell: str = ""
    pronunciationGlossary: list[dict] = Field(default_factory=list)
