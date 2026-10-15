import asyncio
import json
import random
import time
from typing import Any

import httpx

from src.providers.errors import ProviderRequestError

ATTEMPTS = 3
MAX_RATE_LIMIT_WAIT_S = 65.0

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(follow_redirects=True)
    return _client


def _backoff(attempt: int) -> float:
    base = min(0.5 * 2**attempt, 8.0)
    return base + random.random() * base * 0.5


def _rate_limit_wait(res: httpx.Response) -> float | None:
    retry_after = res.headers.get("retry-after")
    if retry_after and retry_after.strip().isdigit():
        return float(retry_after)
    if res.headers.get("x-ratelimit-remaining") == "0":
        reset = res.headers.get("x-ratelimit-reset")
        if reset and reset.strip().isdigit():
            return max(float(reset) - time.time(), 0.0) + 1.0
    return None


def _parse(res: httpx.Response) -> Any:
    text = res.text
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return text


async def vendor_request(
    provider_id: str,
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    query: dict[str, Any] | None = None,
    timeout_s: float = 30.0,
) -> Any:
    params = {k: v for k, v in (query or {}).items() if v is not None}
    last: ProviderRequestError | None = None
    for attempt in range(ATTEMPTS):
        try:
            res = await client().request(
                method,
                url,
                headers=headers,
                json=json_body,
                params=params,
                timeout=timeout_s,
            )
        except httpx.HTTPError as exc:
            last = ProviderRequestError(provider_id, None, f"{provider_id} is unreachable: {exc}")
            if attempt + 1 < ATTEMPTS:
                await asyncio.sleep(_backoff(attempt))
            continue
        parsed = _parse(res)
        wait = _rate_limit_wait(res) if res.status_code in (403, 429) else None
        if wait is not None and wait <= MAX_RATE_LIMIT_WAIT_S:
            last = ProviderRequestError(
                provider_id, res.status_code, f"{provider_id} is rate limited", parsed
            )
            if attempt + 1 < ATTEMPTS:
                await asyncio.sleep(wait)
            continue
        if res.status_code == 429 or res.status_code >= 500:
            last = ProviderRequestError(
                provider_id, res.status_code, f"{provider_id} answered {res.status_code}", parsed
            )
            if attempt + 1 < ATTEMPTS:
                await asyncio.sleep(_backoff(attempt))
            continue
        if res.status_code >= 400:
            raise ProviderRequestError(
                provider_id, res.status_code, f"{provider_id} answered {res.status_code}", parsed
            )
        return parsed
    assert last is not None
    raise last
