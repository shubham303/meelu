import asyncio
import time
from dataclasses import dataclass
from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.registry import VendorResponse
from src.settings import settings

BASE = "https://api.apify.com/v2"
RUN_TIMEOUT_S = 300
WAIT_S = 60
COST_SETTLE_ATTEMPTS = 5
ACTIVE = ("READY", "RUNNING")
FINISHED = ("SUCCEEDED", "TIMED-OUT")


def configured() -> bool:
    return bool(settings.apify_api_key)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.apify_api_key}"}


async def _run(provider_id: str, run_id: str, wait_s: int = 0) -> dict:
    res = await vendor_request(
        provider_id,
        f"{BASE}/actor-runs/{run_id}",
        headers=_headers(),
        query={"waitForFinish": wait_s or None},
        timeout_s=wait_s + 30,
    )
    return (res or {}).get("data") or {}


async def _abort(provider_id: str, run_id: str) -> None:
    try:
        await vendor_request(
            provider_id, f"{BASE}/actor-runs/{run_id}/abort", method="POST", headers=_headers()
        )
    except ProviderRequestError:
        pass


DATASET_ITEM_EVENT = "apify-default-dataset-item"


@dataclass(frozen=True)
class ChargeEvents:
    result: str = DATASET_ITEM_EVENT
    start: str | None = None


def _usage_micros(run: dict) -> int:
    cost = run.get("usageTotalUsd")
    return round(cost * 1_000_000) if isinstance(cost, (int, float)) else 0


def _event_estimate_micros(run: dict, charges: ChargeEvents, item_count: int) -> int:
    events = ((run.get("pricingInfo") or {}).get("pricingPerEvent") or {}).get(
        "actorChargeEvents"
    ) or {}
    counts = dict(run.get("chargedEventCounts") or {})
    floors = {charges.result: item_count, **({charges.start: 1} if charges.start else {})}
    for event, floor in floors.items():
        if event in events:
            counts[event] = max(counts.get(event) or 0, floor)
    total = 0.0
    for event, count in counts.items():
        price = (events.get(event) or {}).get("eventPriceUsd")
        if isinstance(price, (int, float)) and count:
            total += price * count
    return round(total * 1_000_000)


async def _settled_cost(provider_id: str, run: dict, charges: ChargeEvents, item_count: int) -> int:
    previous = -1
    for attempt in range(COST_SETTLE_ATTEMPTS):
        usage = _usage_micros(run)
        estimate = _event_estimate_micros(run, charges, item_count)
        if usage >= estimate and usage == previous:
            break
        previous = usage
        await asyncio.sleep(1 + attempt)
        run = await _run(provider_id, run["id"])
    return max(_usage_micros(run), _event_estimate_micros(run, charges, item_count))


async def run_actor(
    provider_id: str,
    actor_id: str,
    actor_input: dict[str, Any],
    max_items: int,
    charges: ChargeEvents = ChargeEvents(),
) -> VendorResponse:
    started = await vendor_request(
        provider_id,
        f"{BASE}/acts/{actor_id}/runs",
        method="POST",
        headers=_headers(),
        json_body=actor_input,
        query={
            "waitForFinish": WAIT_S,
            "timeout": RUN_TIMEOUT_S,
            "maxItems": max_items,
            "maxTotalChargeUsd": settings.apify_max_charge_usd_per_run,
        },
        timeout_s=WAIT_S + 30,
    )
    run = (started or {}).get("data") or {}
    if not run.get("id"):
        raise ProviderRequestError(provider_id, 502, f"Apify did not start {actor_id}", started)

    deadline = time.monotonic() + RUN_TIMEOUT_S + WAIT_S
    while run.get("status") in ACTIVE:
        if time.monotonic() > deadline:
            await _abort(provider_id, run["id"])
            raise ProviderRequestError(provider_id, 504, f"Apify run of {actor_id} did not finish")
        run = await _run(provider_id, run["id"], WAIT_S)

    if run.get("status") not in FINISHED or not run.get("defaultDatasetId"):
        raise ProviderRequestError(
            provider_id, 502, f"Apify run of {actor_id} ended {run.get('status')}", run
        )

    items = await vendor_request(
        provider_id,
        f"{BASE}/datasets/{run['defaultDatasetId']}/items",
        headers=_headers(),
        query={"format": "json", "clean": "true", "limit": max_items},
        timeout_s=120,
    )
    rows = items if isinstance(items, list) else []
    return VendorResponse(rows, await _settled_cost(provider_id, run, charges, len(rows)))
