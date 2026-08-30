"""Documentação interativa com assets locais quando disponíveis.

Por padrão o FastAPI carrega o Swagger UI de um CDN. Numa apresentação isso é um
ponto único de falha fora do nosso controle: sem internet — ou com a rede do
local ruim — a página de documentação abre em branco.

Se os arquivos estiverem em `app/interfaces/http/static/`, servimos de lá.
Caso contrário, cai para o CDN. Ver `static/README.md` para baixá-los.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"

SWAGGER_JS = "swagger-ui-bundle.js"
SWAGGER_CSS = "swagger-ui.css"
REDOC_JS = "redoc.standalone.js"


def assets_available() -> bool:
    return (STATIC_DIR / SWAGGER_JS).is_file() and (STATIC_DIR / SWAGGER_CSS).is_file()


def register(app: FastAPI) -> None:
    """Substitui /docs e /redoc por versões servidas localmente."""
    if not assets_available():
        return  # mantém o comportamento padrão do FastAPI (CDN)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # remove as rotas padrão para registrar as nossas
    app.routes[:] = [r for r in app.routes if getattr(r, "path", None) not in ("/docs", "/redoc")]

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} — documentação",
            swagger_js_url=f"/static/{SWAGGER_JS}",
            swagger_css_url=f"/static/{SWAGGER_CSS}",
        )

    @app.get("/redoc", include_in_schema=False)
    async def redoc() -> HTMLResponse:
        redoc_js = STATIC_DIR / REDOC_JS
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} — referência",
            redoc_js_url=f"/static/{REDOC_JS}" if redoc_js.is_file()
            else "https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        )
