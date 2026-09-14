import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.core.logging import get_logger


class IntegrationError(Exception):
    def __init__(self, status: int | None, message: str, body: Any = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.body = body


class TransientIntegrationError(IntegrationError):
    pass


class HttpIntegration:
    name = "integration"
    base_url = ""
    timeout_seconds = 30.0
    attempts = 3

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._log = get_logger(f"integrations.{self.name}.request")

    def auth_headers(self) -> dict[str, str]:
        return {}

    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)
        return self._client

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(TransientIntegrationError),
            wait=wait_exponential_jitter(initial=0.5, max=8.0),
            stop=stop_after_attempt(self.attempts),
            reraise=True,
        ):
            with attempt:
                return await self._request_once(method, path, json, params, headers)

    async def _request_once(
        self,
        method: str,
        path: str,
        json: Any,
        params: dict[str, Any] | None,
        headers: dict[str, str] | None,
    ) -> Any:
        started = time.monotonic()
        try:
            res = await self.client().request(
                method,
                path,
                json=json,
                params=params,
                headers={**self.auth_headers(), **(headers or {})},
            )
        except httpx.TimeoutException as e:
            self._log.warning("timeout", method=method, path=path)
            raise TransientIntegrationError(None, f"{self.name} timed out") from e
        except httpx.TransportError as e:
            self._log.warning("unreachable", method=method, path=path, error=str(e))
            raise TransientIntegrationError(None, f"{self.name} is unreachable: {e}") from e

        elapsed_ms = round((time.monotonic() - started) * 1000)
        self._log.info("response", method=method, path=path, status=res.status_code, ms=elapsed_ms)

        body = self._read_body(res)
        if res.status_code == 429 or res.status_code >= 500:
            raise TransientIntegrationError(
                res.status_code, f"{self.name} answered {res.status_code}", body
            )
        if res.status_code >= 400:
            raise IntegrationError(res.status_code, f"{self.name} answered {res.status_code}", body)
        return body

    @staticmethod
    def _read_body(res: httpx.Response) -> Any:
        if not res.content:
            return None
        try:
            return res.json()
        except ValueError:
            return res.text

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
