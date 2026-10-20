from src.providers import apify
from src.providers.apify import ChargeEvents

ACTOR = {
    "pricingInfos": [
        {
            "startedAt": "2025-01-01T00:00:00.000Z",
            "pricingPerEvent": {
                "actorChargeEvents": {"result-item": {"eventPriceUsd": 0.01}},
            },
        },
        {
            "startedAt": "2026-06-01T00:00:00.000Z",
            "pricingPerEvent": {
                "actorChargeEvents": {
                    "result-item": {
                        "eventTieredPricingUsd": {
                            "FREE": {"tieredEventPriceUsd": 0.004},
                            "GOLD": {"tieredEventPriceUsd": 0.002},
                        }
                    },
                    "init": {"eventPriceUsd": 0.00005},
                }
            },
        },
        {
            "startedAt": "2999-01-01T00:00:00.000Z",
            "pricingPerEvent": {"actorChargeEvents": {"result-item": {"eventPriceUsd": 1.0}}},
        },
    ]
}


async def test_max_charge_uses_the_current_highest_tier_price(monkeypatch):
    async def vendor_request(provider_id, url, **kwargs):
        return {"data": ACTOR}

    monkeypatch.setattr(apify, "vendor_request", vendor_request)
    apify._prices.clear()

    charges = ChargeEvents(result="result-item", start="init")
    micros = await apify.max_charge_micros("apify/a", "a~b", charges, runs=40, results=1000)
    assert micros == round((0.004 * 1000 + 0.00005 * 40) * 1_000_000)

    unknown = ChargeEvents(result="apify-default-dataset-item")
    assert await apify.max_charge_micros("apify/a", "a~b", unknown, runs=1, results=10) is None
