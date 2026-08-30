"""Carregador dos prompts em app/prompts/.

Substituicao simples de {{variavel}}. Em desenvolvimento rele o arquivo a cada
chamada, para que ajustar um prompt nao exija reiniciar a API.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ...settings import get_settings

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class PromptNotFound(FileNotFoundError):
    pass


class PromptLoader:
    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or PROMPTS_DIR
        self._hot_reload = get_settings().environment == "development"

    def raw(self, name: str) -> str:
        return self._read_uncached(name) if self._hot_reload else self._read_cached(name)

    @lru_cache(maxsize=32)  # noqa: B019
    def _read_cached(self, name: str) -> str:
        return self._read_uncached(name)

    def _read_uncached(self, name: str) -> str:
        path = self._dir / f"{name}.md"
        if not path.is_file():
            raise PromptNotFound(f"Prompt '{name}' não encontrado em {self._dir}")
        return path.read_text(encoding="utf-8")

    def render(self, name: str, **variables) -> str:
        text = self.raw(name)
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def available(self) -> list[str]:
        return sorted(p.stem for p in self._dir.glob("*.md") if p.stem != "README")
