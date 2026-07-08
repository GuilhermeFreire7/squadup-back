from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(examples=["USER_NOT_FOUND"])
    message: str = Field(examples=["Usuário não encontrado."])


class ErrorResponse(BaseModel):
    detail: ErrorDetail


def error_responses(*errors: tuple[int, str, str]) -> dict[int | str, dict[str, Any]]:
    """Monta o `responses=` do FastAPI a partir de tuplas (status_code, SHORT_CODE, mensagem).

    SHORT_CODEs que compartilham o mesmo status HTTP viram exemplos nomeados no mesmo
    media type, para o Swagger UI listar todos os erros possíveis de um endpoint em vez
    de só o formato genérico de `HTTPException`.
    """
    grouped: dict[int, dict[str, dict[str, Any]]] = {}
    for status_code, code, message in errors:
        grouped.setdefault(status_code, {})[code] = {
            "value": {"detail": {"code": code, "message": message}}
        }

    return {
        status_code: {
            "model": ErrorResponse,
            "content": {"application/json": {"examples": examples}},
        }
        for status_code, examples in grouped.items()
    }


AUTH_ERRORS: list[tuple[int, str, str]] = [
    (401, "INVALID_CREDENTIALS", "Não foi possível validar as credenciais."),
]

ADMIN_ERRORS: list[tuple[int, str, str]] = [
    *AUTH_ERRORS,
    (403, "ADMIN_ONLY", "Apenas administradores podem acessar este recurso."),
]
