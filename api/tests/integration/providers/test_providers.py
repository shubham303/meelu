from datetime import timedelta

import pytest

from src.core.database import unit_of_work
from src.credits.schemas import GrantRequest
from src.credits.service import InsufficientCreditsError, credit_service
from src.providers.errors import ProviderRequestError
from src.providers.registry import Caller, ProviderAdapter, ProviderFacade, VendorResponse
from src.providers.seo_data.adapter import DEFAULT_LOCALE
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

    async def get(self, caller, key):
        return await self.fetch(
            caller,
            "thing.get",
            lambda _: {"key": key},
            lambda a: a.get(key),
            timedelta(hours=1),
        )


async def user_id_of(client, email):
    await signup(client, email)
    return (await client.get("/api/auth/me")).json()["data"]["id"]


async def test_signup_grants_credits_and_ledger(client, email):
    from tests.integration.credits.test_site_billing import make_operator

    await signup(client, email)
    r = await client.get("/api/v1/credits")
    assert r.status_code == 200
    assert r.json()["data"]["balanceUsd"] == 1.0

    await make_operator((await client.get("/api/auth/me")).json()["data"]["id"])
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 2.5, "note": "top up"})
    assert r.json()["data"]["balanceUsd"] == 3.5

    r = await client.get("/api/v1/credits/ledger")
    kinds = [e["kind"] for e in r.json()["data"]]
    assert kinds == ["grant", "grant"]
    assert r.json()["data"][0]["note"] == "top up"


async def test_facade_falls_back_caches_and_charges(client, email):
    user_id = await user_id_of(client, email)
    flaky, stable = FlakyAdapter(), StableAdapter()
    facade = ThingFacade([flaky, stable])
    caller = Caller(user_id=user_id)

    first = await facade.get(caller, "a")
    second = await facade.get(caller, "a")
    assert first == second == {"key": "a", "n": 1}
    assert flaky.calls == 1 and stable.calls == 1

    r = await client.get("/api/v1/credits")
    assert r.json()["data"]["balanceUsd"] == 0.75

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
        await credit_service.grant(db, user_id, GrantRequest(amount_usd=0.000001))
        await db.execute(
            __import__("sqlalchemy").text(
                "update credit_account set balance_micros = 0 where user_id = :u"
            ),
            {"u": user_id},
        )
    with pytest.raises(InsufficientCreditsError):
        await facade.get(caller, "b")
    assert stable.calls == 0


async def test_raises_when_every_adapter_fails(client, email):
    user_id = await user_id_of(client, email)
    facade = ThingFacade([FlakyAdapter()])
    with pytest.raises(ProviderRequestError):
        await facade.get(Caller(user_id=user_id), "c")
    r = await client.get("/api/v1/providers/calls?domain=things")
    assert r.json()["data"][0]["status"] == "error"


async def test_status_and_platform_listing(client, email):
    await signup(client, email)
    r = await client.get("/api/v1/providers/status")
    domains = {d["domain"]: d for d in r.json()["data"]}
    assert set(domains) == {
        "seo-data",
        "social-listening",
        "people-search",
        "json-data-extractor",
    }
    assert domains["seo-data"]["adapters"][0]["id"] == "dataforseo"

    r = await client.get("/api/v1/providers/social-listening/platforms")
    platforms = {p["id"]: p for p in r.json()["data"]["platforms"]}
    assert platforms["hackernews"]["available"] is True
    assert platforms["reddit"]["available"] == social_search.supports("search.reddit")
    assert set(platforms) == {
        "hackernews",
        "stackexchange",
        "devto",
        "github",
        "reddit",
        "x",
        "linkedin",
        "bluesky",
        "facebook",
    }


async def test_seo_tool_shapes_without_vendor(client, email):
    user_id = await user_id_of(client, email)
    caller = Caller(user_id=user_id)
    assert await seo_data.keyword_overview(caller, [], DEFAULT_LOCALE) == []


async def test_social_search_falls_back_to_second_actor(client, email, monkeypatch):
    from src.providers import apify
    from src.settings import settings

    monkeypatch.setattr(settings, "apify_api_key", "test-key")
    calls = []

    async def run_actor(provider_id, actor_id, actor_input, max_items, charges):
        calls.append((actor_id, max_items, actor_input.get("maxPosts")))
        if actor_id == "harshmaur~reddit-scraper-pro":
            raise ProviderRequestError(provider_id, 502, "down")
        return VendorResponse(
            [
                {
                    "kind": "post",
                    "id": "abc",
                    "title": f"{actor_input['queries'][0]} question",
                    "body": "body",
                    "author": "amg",
                    "subreddit": "SEO",
                    "created_utc": "2099-01-01T00:00:00Z",
                    "url": "https://www.reddit.com/r/SEO/comments/abc/q/",
                }
            ],
            12_000,
        )

    monkeypatch.setattr(apify, "run_actor", run_actor)
    user_id = await user_id_of(client, email)
    before = (await client.get("/api/v1/credits")).json()["data"]["balanceMicros"]

    keywords = [f"kw-{email}", "second", "third", "fourth"]
    result = await social_search.search_platform(
        Caller(user_id=user_id), "reddit", keywords, None, 25
    )
    assert [p["id"] for p in result["posts"]] == ["abc"]
    assert result["failedKeywords"] == []

    assert calls == [
        ("harshmaur~reddit-scraper-pro", 100, None),
        ("fatihtahta~reddit-scraper-search-fast", 100, 25),
    ]
    after = (await client.get("/api/v1/credits")).json()["data"]["balanceMicros"]
    assert before - after == 12_000

    r = await client.get("/api/v1/providers/calls?domain=social-listening")
    providers = {c["provider"] for c in r.json()["data"]}
    assert "apify/fatihtahta~reddit-scraper-search-fast" in providers


async def test_facebook_runs_once_per_keyword(client, email, monkeypatch):
    from src.providers import apify
    from src.settings import settings

    monkeypatch.setattr(settings, "apify_api_key", "test-key")
    queries = []

    async def run_actor(provider_id, actor_id, actor_input, max_items, charges):
        queries.append((actor_input["query"], max_items))
        if actor_input["query"] == "broken":
            raise ProviderRequestError(provider_id, 502, "down")
        return VendorResponse(
            [
                {
                    "postId": f"{actor_input['query']}-1",
                    "url": f"https://www.facebook.com/x/posts/{actor_input['query']}",
                    "postText": actor_input["query"],
                    "timestamp": 4070908800000,
                    "author": {"name": "A"},
                }
            ],
            1_000,
        )

    monkeypatch.setattr(apify, "run_actor", run_actor)
    user_id = await user_id_of(client, email)
    result = await social_search.search_platform(
        Caller(user_id=user_id), "facebook", ["one", "broken", "two"], None, 25
    )
    assert sorted(queries) == [("broken", 25), ("one", 25), ("two", 25)]
    assert sorted(p["id"] for p in result["posts"]) == ["one-1", "two-1"]
    assert result["failedKeywords"] == ["broken"]


async def test_public_api_reports_failed_keywords(client, email, monkeypatch):
    from src.providers.social_search import meelu_public

    async def vendor_request(provider_id, url, *, query=None, **kwargs):
        if query["query"] == "broken":
            raise ProviderRequestError(provider_id, 502, "down")
        return {
            "hits": [
                {
                    "objectID": f"{query['query']}-{query['tags']}",
                    "title": query["query"],
                    "created_at": "2099-01-01T00:00:00Z",
                    "author": "pg",
                }
            ]
        }

    monkeypatch.setattr(meelu_public, "vendor_request", vendor_request)
    user_id = await user_id_of(client, email)
    result = await social_search.search_platform(
        Caller(user_id=user_id), "hackernews", ["fine", "broken"], None, 25
    )
    assert len(result["posts"]) == 2
    assert result["failedKeywords"] == ["broken"]

    with pytest.raises(ProviderRequestError):
        await social_search.search_platform(
            Caller(user_id=user_id), "hackernews", ["broken"], None, 25
        )
