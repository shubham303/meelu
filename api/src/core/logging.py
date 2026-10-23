import logging
import time

import sentry_sdk
import structlog
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


def configure_error_reporting() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        send_default_pii=False,
        traces_sample_rate=0,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()


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
