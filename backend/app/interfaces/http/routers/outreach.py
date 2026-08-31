"""Contato ativo — quando a Claro inicia a conversa."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....application.dto.outreach_command import SendOutreachCommand
from ....application.use_cases.outreach import OutreachBlocked
from ....container import Container, get_container
from ..mappers import eligible_to_dto
from ..schemas.eligible_customer_response import EligibleCustomerResponse
from ..schemas.error_response import ErrorResponse
from ..schemas.outreach_result_response import OutreachResultResponse

router = APIRouter(prefix="/api/v1/outreach", tags=["Console · Contato Ativo"])


@router.get(
    "/eligible",
    response_model=list[EligibleCustomerResponse],
    summary="Clientes elegíveis a contato ativo",
    description=(
        "Lista os clientes que o hub considera abordáveis, **com o motivo explícito** de "
        "cada seleção e os impedimentos que porventura existam.\n\n"
        "Dois critérios governam a lista, e ambos vêm da política de mensageria:\n\n"
        "- **Consentimento.** Sem autorização para receber oferta, a abordagem comercial "
        "não pode sair. O cliente aparece na lista, mas bloqueado.\n"
        "- **Janela de atendimento.** Nas 24 horas seguintes à última mensagem do cliente "
        "a empresa responde livremente. Passado esse prazo, `requires_template` volta "
        "`true` e o contato só sai por um modelo previamente aprovado.\n\n"
        "Bloqueio aqui não é erro: é a política funcionando."
    ),
)
async def list_eligible(
    only_contactable: bool = Query(
        False, description="Quando verdadeiro, esconde os clientes bloqueados."),
    container: Container = Depends(get_container),
) -> list[EligibleCustomerResponse]:
    items = await container.list_eligible_customers.execute(only_contactable)
    return [eligible_to_dto(item) for item in items]


@router.post(
    "/send",
    response_model=OutreachResultResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Política de contato impediu o envio"},
        404: {"model": ErrorResponse, "description": "Cliente não encontrado"},
    },
    summary="Abordar um cliente com uma oferta",
    description=(
        "Abre uma conversa iniciada pela empresa e entrega a oferta ao cliente.\n\n"
        "A elegibilidade é reavaliada no momento do envio — não basta o cliente ter "
        "aparecido na lista minutos antes. Se houver qualquer impedimento, a chamada é "
        "recusada com o motivo.\n\n"
        "Dentro da janela de atendimento a mensagem é redigida na hora, considerando o "
        "perfil do cliente e o motivo da abordagem. Fora dela, sai um modelo aprovado com "
        "as variáveis preenchidas, e `used_template` volta `true`."
    ),
)
async def send_outreach(
    payload: dict,
    container: Container = Depends(get_container),
) -> OutreachResultResponse:
    from ..schemas.send_outreach_request import SendOutreachRequest

    request = SendOutreachRequest(**payload)
    try:
        result = await container.send_outreach.execute(SendOutreachCommand(
            customer_id=request.customer_id, offer_id=request.offer_id,
            channel=request.channel, agent=request.agent,
            custom_message=request.custom_message,
        ))
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except OutreachBlocked as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc

    return OutreachResultResponse(
        conversation_id=result.conversation_id, customer_id=result.customer_id,
        message=result.message, channel=result.channel,
        template_category=result.template_category, used_template=result.used_template,
        response_source=result.response_source.value,
    )
