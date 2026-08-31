"""Metadados visuais de um canal, separados da regra de negócio."""
from __future__ import annotations

from pydantic import BaseModel


class ChannelPresentation(BaseModel):
    color: str = ""
    bgColor: str = ""
    iconColor: str = ""
