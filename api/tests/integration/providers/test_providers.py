from datetime import timedelta

import pytest

from src.core.database import unit_of_work
from src.credits import service as credits
from src.providers.errors import ProviderRequestError
from src.providers.registry import Caller, ProviderAdapter, ProviderFacade, VendorResponse
from src.providers.seo_data.service import seo_data
from src.providers.social_search.service import social_search
from tests.conftest import signup


class FlakyAdapter(ProviderAdapter):
    id = "flaky"
    name = "Flaky"
    capabilities = frozenset({"thing.get"})

    def __init__(self):
        self.calls = 0

    async def get(self, key):
        self.calls += 1
        raise ProviderRequestError(self.id, 503, "flaky down")


class StableAdapter(ProviderAdapter):
    id = "stable"
    name = "Stable"
    capabilities = frozenset({"thing.get"})

    def __init__(self, cost=250_000):
        self.calls = 0
        self.cost = cost

    async def get(self, key):
        self.calls += 1
        return VendorResponse({"key": key, "n": self.calls}, self.cost)


class ThingFacade(ProviderFacade):
    domain = "things"
    label = "things"

    async def get(self, db, caller, key):
        return await self.fetch(
            db, caller, "thing.get", {"key": key}, lambda a: a.get(key), timedelta(hours=1)
        )


async def user_id_of(client, email):
    await signup(client, email)
    return (await client.get("/api/auth/me")).json()["data"]["id"]


async def test_signup_grants_credits_and_ledger(client, email):
    await signup(client, email)
    r = await client.get("/api/v1/credits")
    assert r.status_code == 200
    assert r.json()["data"]["balanceUsd"] == 5.0

    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 2.5, "note": "top up"})
    assert r.json()["data"]["balanceUsd"] == 7.5

    r = await client.get("/api/v1/credits/ledger")
    kinds = [e["kind"] for e in r.json()["data"]]
    assert kinds == ["grant", "grant"]
    assert r.json()["data"][0]["note"] == "top up"


async def test_facade_falls_back_caches_and_charges(client, email):
    user_id = await user_id_of(client, email)
    flaky, stable = FlakyAdapter(), StableAdapter()
    facade = ThingFacade([flaky, stable])
    caller = Caller(user_id=user_id)

    async with unit_of_work() as db:
        first = await facade.get(db, caller, "a")
    async with unit_of_work() as db:
        second = await facade.get(db, caller, "a")
    assert first == second == {"key": "a", "n": 1}
    assert flaky.calls == 1 and stable.calls == 1

    r = await client.get("/api/v1/credits")
    assert r.json()["data"]["balanceUsd"] == 4.75

    r = await client.get("/api/v1/providers/calls?domain=things")
    calls = r.json()["data"]
    assert [c["cacheHit"] for c in calls] == [True, False]
    assert calls[1]["provider"] == "stable"
    assert calls[1]["chargedMicros"] == 250_000
    assert calls[1]["vendorCostMicros"] == 250_000

    r = await client.get("/api/v1/credits/ledger")
    usage = next(e for e in r.json()["data"] if e["kind"] == "usage")
    assert usage["providerCallId"] == calls[1]["id"]
    assert usage["deltaMicros"] == -250_000


async def test_facade_refuses_without_credits(client, email):
    user_id = await user_id_of(client, email)
    stable = StableAdapter()
    facade = ThingFacade([stable])
    caller = Caller(user_id=user_id)
    async with unit_of_work() as db:
        await credits.grant(db, user_id, credits.GrantRequest(amount_usd=0.000001))
        await db.execute(
            __import__("sqlalchemy").text(
                "update credit_account set balance_micros = 0 where user_id = :u"
            ),
            {"u": user_id},
        )
    with pytest.raises(credits.InsufficientCreditsError):
        async with unit_of_work() as db:
            await facade.get(db, caller, "b")
    assert stable.calls == 0


async def test_raises_when_every_adapter_fails(client, email):
    user_id = await user_id_of(client, email)
    facade = ThingFacade([FlakyAdapter()])
    with pytest.raises(ProviderRequestError):
        async with unit_of_work() as db:
            await facade.get(db, Caller(user_id=user_id), "c")
    r = await client.get("/api/v1/providers/calls?domain=things")
    assert r.json()["data"][0]["status"] == "error"


async def test_status_and_platform_listing(client, email):
    await signup(client, email)
    r = await client.get("/api/v1/providers/status")
    domains = {d["domain"]: d for d in r.json()["data"]}
    assert set(domains) == {
        "seo-data",
        "social-listening",
        "prospect-sources",
        "json-data-extractor",
        "llm-judge",
    }
    assert domains["seo-data"]["adapters"][0]["id"] == "dataforseo"

    r = await client.get("/api/v1/providers/social-listening/platforms")
    platforms = {p["id"]: p for p in r.json()["data"]["platforms"]}
    assert platforms["hackernews"]["available"] is True
    assert platforms["reddit"]["available"] == social_search.supports("search.reddit")

    r = await client.post(
        "/api/v1/providers/social-listening/search",
        json={"platform": "nowhere", "keywords": ["x"]},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "no_provider"


async def test_seo_tool_shapes_without_vendor(client, email):
    user_id = await user_id_of(client, email)
    async with unit_of_work() as db:
        assert await seo_data.keyword_facts(db, Caller(user_id=user_id), []) == {"facts": []}
