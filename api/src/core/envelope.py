import json

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

RAW_PATHS = ("/api/v1/llm/v1/",)


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": {"message": message}}, status_code=status)


def _field(loc: tuple) -> str:
    parts = [str(p) for p in loc]
    if parts and parts[0] in ("body", "query", "path", "header"):
        parts = parts[1:]
    return ".".join(parts)


def _validation_message(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request."
    missing = [_field(e.get("loc", ())) for e in errors if e.get("type") == "missing"]
    if missing:
        return f"Missing required field(s): {', '.join(missing)}"
    first = errors[0]
    msg = str(first.get("msg", "Invalid request."))
    if msg.startswith("Value error, "):
        return msg[len("Value error, ") :]
    field = _field(first.get("loc", ()))
    return f"{field}: {msg}" if field else msg


class EnvelopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        path = request.url.path
        if not path.startswith("/api/") or path.startswith(RAW_PATHS):
            return response
        if not (200 <= response.status_code < 300) or response.status_code == 204:
            return response
        if not response.headers.get("content-type", "").startswith("application/json"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        if not body:
            return Response(status_code=response.status_code, headers=dict(response.headers))
        payload = json.loads(body)
        if not (isinstance(payload, dict) and "data" in payload and "pagination" in payload):
            payload = {"data": payload}
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return JSONResponse(payload, status_code=response.status_code, headers=headers)


def install_envelope(app: FastAPI) -> None:
    app.add_middleware(EnvelopeMiddleware)

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
        return _error(exc.status_code, detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(400, _validation_message(exc))
