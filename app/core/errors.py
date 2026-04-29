from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorPayload = Field(description="Standard error envelope.")


class AppError(Exception):
    """Base for all application errors. Subclasses set ``code`` and ``http_status``."""

    code: str = "app_error"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ConfigurationError(AppError):
    """Invalid or missing configuration detected at runtime."""

    code = "configuration_error"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR


class ValidationAppError(AppError):
    """Domain-level validation failure (distinct from FastAPI request validation)."""

    code = "validation_error"
    http_status = status.HTTP_422_UNPROCESSABLE_CONTENT


class NotFoundAppError(AppError):
    """Requested resource was not found."""

    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND


class ExternalServiceError(AppError):
    """An external API (PVGIS, BDNS, geocoding, LLM provider) failed or returned bad data."""

    code = "external_service_error"
    http_status = status.HTTP_502_BAD_GATEWAY


class AgentExecutionError(AppError):
    """The agent failed to plan or execute a step."""

    code = "agent_execution_error"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR


class ToolExecutionError(AppError):
    """A tool invoked by the agent raised or returned an unrecoverable error."""

    code = "tool_execution_error"
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR


def _envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return ErrorResponse(error=ErrorPayload(code=code, message=message, details=details)).model_dump(
        exclude_none=True
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("app_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=exc.http_status,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_envelope("validation_error", "Request validation failed", {"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "Unexpected server error"),
        )
