"""Ponto de entrada da API.

Camada mais externa da arquitetura: monta o FastAPI, liga o container no ciclo de
vida da aplicação e registra os routers. Não contém regra de negócio nenhuma —
se houvesse, estaria na camada errada.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .container import container
from .interfaces.http import docs as local_docs
from .interfaces.http import openapi as spec
from .interfaces.http import spa
from .interfaces.http.routers import (channels, conversations, customers, dashboard,
                                      operations, outreach, studio, whatsapp)
from .settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hub")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await container.startup()
    settings = get_settings()
    log.info("%s v%s pronto (%s)", settings.app_name, settings.version, settings.environment)
    yield
    await container.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=spec.DESCRIPTION,
        openapi_tags=spec.TAGS,
        contact=spec.CONTACT,
        license_info=spec.LICENSE,
        servers=spec.SERVERS,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ingestão primeiro: é a família que um integrador de canal precisa ler.
    app.include_router(channels.router)
    app.include_router(whatsapp.router)
    app.include_router(conversations.router)
    app.include_router(customers.router)
    app.include_router(dashboard.router)
    app.include_router(outreach.router)
    app.include_router(studio.router)
    app.include_router(operations.router)

    # Serve o Swagger UI localmente quando os assets estiverem presentes,
    # para que a documentação não dependa de CDN durante a demonstração.
    local_docs.register(app)

    # Por último, e só na imagem de implantação: o console embutido. Precisa vir
    # depois de todos os routers porque a rota curinga da SPA engoliria
    # qualquer caminho registrado depois dela.
    if not spa.register(app):
        spa.register_root_redirect(app)

    return app


app = create_app()
