import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.agents.memory import aclose_agent_memory_resources
from app.api.routes import chat, health, traces
from app.core.config import get_settings
from app.core.constants import API_DESCRIPTION, API_TITLE, API_VERSION, REQUEST_ID_HEADER
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import close_db_resources, create_db_and_tables


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.app_env != "development")
    create_db_and_tables()
    log = get_logger(__name__)
    log.info("app_startup", service=settings.app_name, env=settings.app_env, version=API_VERSION)
    yield
    await aclose_agent_memory_resources()
    close_db_resources()
    log.info("app_shutdown")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a request_id into structlog contextvars for the duration of the request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        try:
            response: Response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(traces.router)
    return app


app = create_app()
