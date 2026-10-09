from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.settings import settings

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
TRUSTED_FETCH_SITES = frozenset({"same-origin", "none"})
EXEMPT_PATHS = frozenset({"/api/v1/payments/webhooks/dodo"})


def trusted_origins() -> frozenset[str]:
    return frozenset(o.rstrip("/") for o in [*settings.cors_origins, *settings.app_origins])


def cross_site_cookie_request(method: str, path: str, headers: Headers) -> bool:
    if method not in UNSAFE_METHODS or path in EXEMPT_PATHS:
        return False
    if "x-api-key" in headers:
        return False
    fetch_site = headers.get("sec-fetch-site")
    origin = headers.get("origin")
    if fetch_site is None and origin is None:
        return False
    if fetch_site in TRUSTED_FETCH_SITES:
        return False
    return origin is None or origin.rstrip("/") not in trusted_origins()


class CsrfMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and cross_site_cookie_request(
            scope["method"], scope["path"], Headers(scope=scope)
        ):
            response = JSONResponse(
                {"error": {"message": "Cross-site request refused."}}, status_code=403
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
