"""Serviço dos arquivos do console pela própria API.

Existe para a implantação em nuvem. No Compose, o nginx serve o front e
encaminha `/api` para a API: são dois contêineres numa rede privada, e isso é o
certo em produção. Num PaaS, porém, cada contêiner é um serviço cobrado, com URL
própria, CORS próprio e — no plano gratuito — hibernação própria. Dois serviços
significam dois lugares para dar errado no meio de uma arguição.

Servindo o front pela API, o console e o hub passam a ser uma coisa só: uma URL,
sem CORS, um cold start em vez de dois. O nginx continua valendo para quem sobe
por Compose; este módulo só entra quando existe um `dist/` embutido na imagem.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

log = logging.getLogger("hub.spa")

# Definido pelo Dockerfile de implantação; ausente em desenvolvimento.
DIST = Path("/app/web")


def register(app: FastAPI, dist: Path = DIST) -> bool:
    """Monta o console na raiz, se ele tiver sido embutido na imagem.

    Devolve `True` quando montou, para que o chamador decida o que fazer com a
    rota raiz — sem front embutido ela continua levando à documentação.
    """
    index = dist / "index.html"
    if not index.is_file():
        log.info("Console não embutido nesta imagem — a raiz leva à documentação.")
        return False

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    async def spa(caminho: str):
        """Devolve o arquivo pedido; qualquer outra rota devolve o index.

        O console é uma SPA: `/console/inbox` não é um arquivo no disco, é uma
        rota que o react-router resolve no navegador. Devolver 404 aí quebraria
        justamente o link que alguém compartilhou.
        """
        alvo = (dist / caminho).resolve()
        # `resolve()` antes de comparar: sem isso, "..%2f" escaparia do diretório
        # e a API viraria um leitor de arquivos do contêiner.
        if caminho and alvo.is_file() and alvo.is_relative_to(dist.resolve()):
            return FileResponse(alvo)
        return FileResponse(index)

    log.info("Console embutido servido pela API a partir de %s", dist)
    return True


def register_root_redirect(app: FastAPI) -> None:
    """Raiz levando à documentação — usado quando não há console embutido."""

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/docs")
