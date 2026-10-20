import asyncio
from typing import Any

import httpx

from src.providers.errors import ProviderRequestError
from src.settings import settings

PROVIDER = "composio"
TIMEOUT_S = 30.0
EXECUTE_TIMEOUT_S = 90.0
READ_ATTEMPTS = 3

MANAGED_AUTH = {"type": "use_composio_managed_auth"}
API_KEY_AUTH = {"type": "use_custom_auth", "authScheme": "API_KEY", "credentials": {}}

_client: httpx.AsyncClient | None = None


class ComposioNotConfiguredError(ValueError):
    def __init__(self) -> None:
        super().__init__("Connected apps are not set up on this server yet (no Composio key).")


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(follow_redirects=False)
    return _client


def _headers() -> dict[str, str]:
    if not settings.composio_api_key:
        raise ComposioNotConfiguredError()
    return {"x-api-key": settings.composio_api_key}


def _url(path: str) -> str:
    return f"{settings.composio_base_url.rstrip('/')}{path}"


async def _call(
    path: str,
    *,
    method: str = "GET",
    json_body: Any = None,
    query: dict[str, Any] | None = None,
    timeout_s: float = TIMEOUT_S,
) -> Any:
    attempts = READ_ATTEMPTS if method == "GET" else 1
    params = {k: v for k, v in (query or {}).items() if v is not None}
    last: ProviderRequestError | None = None
    for attempt in range(attempts):
        try:
            res = await _http().request(
                method,
                _url(path),
                headers=_headers(),
                json=json_body,
                params=params,
                timeout=timeout_s,
            )
        except httpx.HTTPError as exc:
            last = ProviderRequestError(PROVIDER, None, f"{PROVIDER} is unreachable: {exc}")
        else:
            body = _parse(res)
            if res.status_code < 300:
                return body
            message = _error_message(body) or f"{PROVIDER} answered {res.status_code}"
            last = ProviderRequestError(PROVIDER, res.status_code, message, body)
            if res.status_code != 429 and res.status_code < 500:
                raise last
        if attempt + 1 < attempts:
            await asyncio.sleep(0.5 * 2**attempt)
    assert last is not None
    raise last


def _parse(res: httpx.Response) -> Any:
    if not res.content:
        return None
    try:
        return res.json()
    except ValueError:
        return {"error": res.text[:500]}


async def auth_configs(toolkit: str) -> list[dict[str, Any]]:
    body = await _call("/auth_configs", query={"toolkit_slug": toolkit, "limit": 200})
    return list((body or {}).get("items") or [])


async def create_auth_config(toolkit: str, auth_config: dict[str, Any]) -> str:
    body = await _call(
        "/auth_configs",
        method="POST",
        json_body={"toolkit": {"slug": toolkit}, "auth_config": auth_config},
    )
    return body["auth_config"]["id"]


async def create_link(auth_config_id: str, user_id: str) -> dict[str, Any]:
    return await _call(
        "/connected_accounts/link",
        method="POST",
        json_body={"auth_config_id": auth_config_id, "user_id": user_id},
    )


async def connected_accounts(account_ids: list[str]) -> list[dict[str, Any]]:
    if not account_ids:
        return []
    body = await _call(
        "/connected_accounts",
        query={"connected_account_ids": ",".join(account_ids), "limit": len(account_ids)},
    )
    return list((body or {}).get("items") or [])


async def delete_account(account_id: str) -> None:
    try:
        await _call(f"/connected_accounts/{account_id}", method="DELETE")
    except ProviderRequestError as exc:
        if exc.status != 404:
            raise


async def tools(slugs: list[str]) -> list[dict[str, Any]]:
    if not slugs:
        return []
    body = await _call("/tools", query={"tool_slugs": ",".join(slugs), "limit": len(slugs)})
    return list((body or {}).get("items") or [])


async def execute(
    slug: str, user_id: str, account_id: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    return await _call(
        f"/tools/execute/{slug}",
        method="POST",
        json_body={"user_id": user_id, "connected_account_id": account_id, "arguments": arguments},
        timeout_s=EXECUTE_TIMEOUT_S,
    )


def _error_message(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if isinstance(error, dict):
        return error.get("message") or None
    return error or body.get("message") or None
