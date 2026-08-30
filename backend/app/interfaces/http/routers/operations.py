"""Operação — saúde do serviço e trilha de auditoria."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ....container import Container, get_container
from ....infrastructure.llm.prompt_loader import PromptLoader
from ..schemas import ComponentHealth, HealthResponse

router = APIRouter(tags=["Operação"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Saúde e modo de operação",
    description=("Diz em que modo cada componente está rodando.\n\n"
                 "`memory (fallback)` significa que a infraestrutura correspondente não "
                 "respondeu e o hub seguiu em memória — o serviço continua funcional, mas "
                 "sem durabilidade. O mesmo vale para o motor de intenção: sem chave de "
                 "LLM, o classificador por regras assume."),
)
async def health(container: Container = Depends(get_container)) -> HealthResponse:
    session_state = await container.sessions.health()
    history_state = await container.conversations.health()
    degraded = "fallback" in session_state or "fallback" in history_state

    return HealthResponse(
        status="degraded" if degraded else "ok",
        version=container.settings.version,
        environment=container.settings.environment,
        components=ComponentHealth(
            session_store=session_state,
            history_store=history_state,
            intent_engine=container.classifier.engine_name,
            backend_systems=container.backends.available,
        ),
    )


@router.get(
    "/api/v1/audit",
    summary="Trilha de auditoria de acesso (LGPD)",
    description=("Registro de todo acesso e tratamento de dado de cliente: ingestão de "
                 "mensagem, consulta de contexto, transferência e alteração de "
                 "configuração.\n\nAtende ao RNF003 — consultar dado de cliente é um evento "
                 "auditável, não uma leitura silenciosa."),
)
async def audit_trail(
    customer_id: str | None = Query(None, description="Filtra por cliente."),
    limit: int = Query(50, ge=1, le=500),
    container: Container = Depends(get_container),
) -> list[dict]:
    return await container.audit.list(customer_id, limit)


@router.get(
    "/api/v1/prompts",
    summary="Listar os prompts carregados",
    description=("Prompts disponíveis em `app/prompts/`. Nenhum texto enviado ao modelo de "
                 "linguagem está escrito em código Python — todos vivem em arquivos "
                 "versionados, editáveis por quem cuida da linguagem da marca."),
)
async def prompts() -> dict:
    loader = PromptLoader()
    return {"available": loader.available(), "directory": "app/prompts"}
