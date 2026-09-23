from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.registry import VendorResponse
from src.settings import settings

RUN_TIMEOUT_S = 300
BASE = "https://api.apify.com/v2"


def configured() -> bool:
    return bool(settings.apify_token)


async def run_actor(provider_id: str, actor_id: str, actor_input: dict[str, Any]) -> VendorResponse:
    token = settings.apify_token
    run = await vendor_request(
        provider_id,
        f"{BASE}/acts/{actor_id}/run-sync",
        method="POST",
        json_body=actor_input,
        query={"token": token, "timeout": RUN_TIMEOUT_S},
        timeout_s=RUN_TIMEOUT_S + 30,
    )
    data = (run or {}).get("data") if isinstance(run, dict) else None
    if not isinstance(data, dict) or not data.get("defaultDatasetId"):
        raise ProviderRequestError(
            provider_id, 502, f"Apify run of {actor_id} returned no dataset", run
        )
    if data.get("status") not in ("SUCCEEDED", "TIMED-OUT"):
        raise ProviderRequestError(
            provider_id, 502, f"Apify run of {actor_id} ended {data.get('status')}", run
        )
    items = await vendor_request(
        provider_id,
        f"{BASE}/datasets/{data['defaultDatasetId']}/items",
        query={"token": token, "format": "json", "clean": "true"},
        timeout_s=120,
    )
    cost = data.get("usageTotalUsd")
    return VendorResponse(
        items if isinstance(items, list) else [],
        round(cost * 1_000_000) if isinstance(cost, (int, float)) else 0,
    )
