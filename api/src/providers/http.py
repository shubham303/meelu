import asyncio
import json
import random
from typing import Any

import httpx

from src.providers.errors import ProviderRequestError

ATTEMPTS = 3

_client: httpx.AsyncClient | None = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(follow_redirects=True)
    return _client


def _backoff(attempt: int) -> float:
    base = min(0.5 * 2**attempt, 8.0)
    return base + random.random() * base * 0.5


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
