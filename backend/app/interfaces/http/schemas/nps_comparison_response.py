"""Comparativo de NPS entre atendimento automatizado e humano."""
from __future__ import annotations

from pydantic import BaseModel, Field


class NpsPercentages(BaseModel):
    promoters: float
    passives: float
    detractors: float


class NpsGroupResponse(BaseModel):
    total: int = Field(description="Notas respondidas neste grupo.")
    average_score: float | None = Field(
        description="Nota média de 0 a 10. Nulo enquanto não houver resposta.")
    nps: float | None = Field(
        description="NPS pela fórmula clássica (% promotores − % detratores).")
    promoters: int
    passives: int = Field(description="Neutros (7 e 8).")
    detractors: int
    percentages: NpsPercentages
    surveys_sent: int = Field(description="Pesquisas enviadas, respondidas ou não.")
    unanswered: int = Field(description="Pesquisas sem nota (recusadas ou ignoradas).")


class NpsComparisonDelta(BaseModel):
    score_difference: float | None = Field(
        description="Nota média do atendente menos a do bot.")
    nps_difference: float | None = Field(description="NPS do atendente menos o do bot.")
    agent_better: bool | None = Field(
        description="Verdadeiro se o atendimento humano teve nota média maior.")


class NpsComparisonResponse(BaseModel):
    area: str
    bot: NpsGroupResponse
    agent: NpsGroupResponse
    overall: NpsGroupResponse
    comparison: NpsComparisonDelta
