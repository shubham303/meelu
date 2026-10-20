import logging
import time

import structlog
from sqlalchemy import Engine, event
from sqlalchemy.pool import QueuePool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.settings import settings


def configure_logging() -> None:
    level = logging.getLevelName(settings.log_level.upper())
    logging.basicConfig(level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()


def log_connection_checkouts(engine: Engine, pool_name: str) -> None:
    log = get_logger()

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:
        pool = engine.pool
        if not isinstance(pool, QueuePool):
            return
        log.info(
            "core.db.connection_acquired",
            pool=pool_name,
            checked_out=pool.checkedout(),
            idle=pool.checkedin(),
            overflow=max(pool.overflow(), 0),
            pool_size=pool.size(),
        )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        log = get_logger()
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        fields = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }
        log.info("core.http.request", **fields)
        if duration_ms >= settings.log_slow_request_ms:
            log.warning(
                "core.http.slow_request", threshold_ms=settings.log_slow_request_ms, **fields
            )
        return response
