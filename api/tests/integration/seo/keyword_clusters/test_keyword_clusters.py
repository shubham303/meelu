import asyncio
import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from src.core.database import unit_of_work
from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.models.provider_cache import ProviderCache
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.keyword_clusters.schemas import CreateClustersRequest
from src.seo.keyword_clusters.service import keyword_cluster_service
from src.sites.service import site_service
from tests.conftest import signup

FACTS = {
    "espresso machine": (10000, 5000, "espresso machine"),
    "best espresso machine": (8000, 3000, "espresso machine"),
    "espresso machine for home": (2000, 900, "espresso machine"),
    "cheap espresso machines": (900, 150, "espresso machine"),
    "espresso machine repair jobs": (500, 300, None),
}


RANKED = {
    "example.com": ["best espresso machine", "milk frother"],
    "rival-a.example": ["espresso machine", "espresso machine for home", "best espresso machine"],
    "rival-b.example": ["espresso machine", "espresso machine for home"],
}


def ranked_item(keyword: str, seat: int) -> dict:
    return {
        "keyword_data": {"keyword": keyword, "keyword_info": {"search_volume": 100}},
        "ranked_serp_element": {
            "serp_item": {"rank_group": seat, "url": f"https://x.example/{seat}", "etv": 10 - seat}
        },
    }


def envelope(items: list[dict]) -> dict:
    return {
        "status_code": 20000,
        "cost": 0.01,
        "tasks": [{"status_code": 20000, "cost": 0.01, "result": [{"items": items}]}],
    }


def serp(results: list[tuple[str, str]]) -> dict:
    items = [
        {
            "type": "organic",
            "rank_group": seat,
            "url": url,
            "domain": url.split("/")[2],
            "title": title,
        }
        for seat, (url, title) in enumerate(results, start=1)
    ]
    return {
        "status_code": 20000,
        "cost": 0.002,
        "tasks": [{"status_code": 20000, "cost": 0.002, "result": [{"items": items}]}],
    }


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []
        self.serp_results: list[tuple[str, str]] = []
        self.ranks: dict[str, tuple[int, int]] = {}

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        endpoint, task = query["endpoint"], query["task"]
        if endpoint == ENDPOINTS["ideas"]:
            body = envelope([{"keyword": k} for k in ("Best Espresso Machine", "milk frother")])
        elif endpoint == ENDPOINTS["suggestions"]:
            body = envelope(
                [{"keyword": "espresso machine for home"}, {"keyword": "cheap espresso machines"}]
            )
        elif endpoint == ENDPOINTS["related"]:
            body = envelope([{"keyword_data": {"keyword": "espresso machine repair jobs"}}])
        elif endpoint == ENDPOINTS["keyword_overview"]:
            body = envelope(
                [
                    {
                        "keyword": k,
                        "keyword_info": {"search_volume": FACTS[k][0]},
                        "clickstream_keyword_info": {"search_volume": FACTS[k][1]},
                        "keyword_properties": {"core_keyword": FACTS[k][2]},
                    }
                    for k in task["keywords"]
                    if k in FACTS
                ]
            )
        elif endpoint == ENDPOINTS["ranked_keywords"]:
            keywords = RANKED.get(task["target"], [])
            body = envelope([ranked_item(k, seat) for seat, k in enumerate(keywords, start=1)])
        elif endpoint == ENDPOINTS["serp"]:
            body = serp(self.serp_results)
        elif endpoint == ENDPOINTS["bulk_pages_summary"]:
            body = envelope(
                [
                    {"url": url, "rank": self.ranks[url][0], "main_domain_rank": self.ranks[url][1]}
                    for url in task["targets"]
                    if url in self.ranks
                ]
            )
        else:
            raise AssertionError(endpoint)
        return VendorResponse(body, 10_000)


class FakeJudge(JsonDataExtractorAdapter):
    id = "fake-judge"
    name = "Fake judge"
    capabilities = frozenset({DECIDE})

    async def decide(self, state, questions):
        answers = {}
        for key, question in questions.items():
            text = question["instructions"]
            if text.startswith("Is "):
                pick = "no" if "jobs" in text else "yes"
            elif text.startswith("Does a person"):
                asked = re.findall(r'"([^"]+)"', text)[0]
                pick = "yes" if asked.startswith("best ") else "no"
            else:
                seat = int(re.findall(r"result (\d+)", text)[0]) - 1
                pick = "none" if "Login" in (state["results"][seat]["title"] or "") else "full"
            answers[key] = {"type": "choice", "choice": pick, "confidence": 0.9}
        return VendorResponse({"model": "fake", "answers": answers}, 100)


@pytest.fixture
def vendor(monkeypatch):
    fake = FakeDataForSeo()
    monkeypatch.setattr(seo_data, "adapters", [fake])
    monkeypatch.setattr(json_data_extractor, "adapters", [FakeJudge()])
    return fake


async def make_site(client, email):
    await signup(client, email)
    user_id = (await client.get("/api/auth/me")).json()["data"]["id"]
    r = await client.post(
        "/api/v1/sites", json={"domain": "example.com", "name": "Example", "markets": ["GB"]}
    )
    assert r.status_code == 201, r.text
    site_id = r.json()["data"]["id"]
    async with unit_of_work() as db:
        site = await site_service.get(db, user_id, site_id)
    return user_id, site, Caller(user_id=user_id, site_id=site_id)


async def create(user_id, site, caller, **body):
    async with unit_of_work() as db:
        return await asyncio.wait_for(
            keyword_cluster_service.create_clusters(
                db, caller, user_id, site, CreateClustersRequest(seeds=["Espresso Machine"], **body)
            ),
            timeout=30,
        )


async def test_noise_then_relevance_then_same_results_split(client, email, vendor):
    user_id, site, caller = await make_site(client, email)

    created = await create(user_id, site, caller)

    assert created.candidates == 6
    assert created.noise == 2
    assert created.irrelevant == 1
    assert created.clusters == 2
    assert [(c.main_keyword, c.size, c.volume) for c in created.top] == [
        ("espresso machine", 2, 5000),
        ("espresso machine for home", 1, 900),
    ]
    overview = next(q for q in vendor.sent if q["endpoint"] == ENDPOINTS["keyword_overview"])
    assert overview["task"]["location_code"] == 2826

    r = await client.get("/api/v1/site/seo/clusters", params={"search": "best"})
    assert r.status_code == 200, r.text
    [cluster] = r.json()["data"]
    assert cluster["mainKeyword"] == "espresso machine"
    assert cluster["keywords"] == ["espresso machine", "best espresso machine"]
    assert cluster["coreKeyword"] == "espresso machine"
    assert cluster["isRanked"] is True
    assert cluster["competitors"] == []

    again = await create(user_id, site, caller)
    assert again.already_clustered == 3
    assert again.clusters == 0


async def test_a_hard_minimum_replaces_the_relative_floor(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    created = await create(user_id, site, caller, min_volume=1000)
    assert created.noise == 4
    assert [c.main_keyword for c in created.top] == ["espresso machine"]


def rival(seat: int, tag: str) -> str:
    return f"https://{tag}{seat}.com/espresso"


async def score(client, email, vendor, rival_rank: int, our_domain_rank: int, tag: str):
    user_id, site, caller = await make_site(client, email)
    await create(user_id, site, caller, min_volume=1000)
    vendor.serp_results = [
        (rival(s, tag), "Login" if s == 3 else f"Guide {s}") for s in range(1, 11)
    ]
    vendor.ranks = {rival(s, tag): (rival_rank, rival_rank) for s in range(1, 11)}
    vendor.ranks["https://example.com/"] = (0, our_domain_rank)
    async with unit_of_work() as db:
        await db.execute(delete(ProviderCache).where(ProviderCache.capability == "serp.organic"))
    async with unit_of_work() as db:
        computed = await asyncio.wait_for(
            keyword_cluster_service.compute_metrics(db, caller, site, None, 10), timeout=30
        )
    assert computed.computed == 1 and computed.failed == []
    r = await client.get("/api/v1/site/seo/clusters")
    return r.json()["data"][0]


async def test_strong_results_above_a_new_page_are_hard_to_win(client, email, vendor):
    cluster = await score(client, email, vendor, rival_rank=500, our_domain_rank=100, tag="strong")
    assert "ourPosition" not in cluster
    assert cluster["likelyPosition"] == 11
    assert cluster["winnability"] < 5
    r = await client.get("/api/v1/site/seo/clusters", params={"ranked": False})
    assert r.json()["data"] == []
    assert cluster["isRanked"] is True
    r = await client.post(f"/api/v1/site/seo/clusters/{cluster['id']}/metrics")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["winnability"] == cluster["winnability"]
    login = next(c for c in cluster["climb"] if c["position"] == 3)
    assert login["intentFit"] == 0.0 and login["passChance"] == 1.0
    assert cluster["intentFit"] == pytest.approx(0.9)


async def test_weak_results_above_a_strong_domain_are_winnable(client, email, vendor):
    cluster = await score(client, email, vendor, rival_rank=5, our_domain_rank=600, tag="weak")
    assert cluster["winnability"] > 70
    assert cluster["likelyPosition"] <= 3


async def clusters_by_main(client) -> dict[str, dict]:
    r = await client.get("/api/v1/site/seo/clusters", params={"page_size": 50})
    assert r.status_code == 200, r.text
    return {c["mainKeyword"]: c for c in r.json()["data"]}


async def test_competitor_keywords_are_what_two_rivals_rank_for_and_we_do_not(
    client, email, vendor
):
    user_id, site, caller = await make_site(client, email)
    r = await client.post(
        "/api/v1/site/seo/competitors/add", json={"items": ["rival-a.example", "rival-b.example"]}
    )
    assert r.status_code == 200, r.text

    created = await create_from(user_id, site, caller, "competitor_keywords")

    assert created.source == "competitor_keywords"
    assert created.candidates == 2
    clusters = await clusters_by_main(client)
    assert set(clusters) == {"espresso machine", "espresso machine for home"}
    for cluster in clusters.values():
        assert cluster["isRanked"] is False
        assert cluster["competitors"] == ["rival-a.example", "rival-b.example"]

    r = await client.post(
        "/api/v1/site/seo/competitors/remove", json={"items": ["rival-b.example"]}
    )
    assert r.status_code == 200, r.text
    clusters = await clusters_by_main(client)
    assert clusters["espresso machine"]["competitors"] == ["rival-a.example"]


async def test_search_console_queries_become_clusters_we_rank_for(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    day = (datetime.now(UTC).date() - timedelta(days=4)).isoformat()
    rows = [
        {
            "query": q,
            "page": "https://example.com/p",
            "device": "DESKTOP",
            "clicks": 1,
            "impressions": 40,
            "position": 12,
        }
        for q in ("espresso machine for home", "espresso machine repair jobs")
    ]
    r = await client.post(
        "/api/v1/site/search-data/rows", json={"days": [{"day": day, "rows": rows}]}
    )
    assert r.status_code == 200, r.text

    created = await create_from(user_id, site, caller, "search_console")

    assert created.candidates == 2
    assert created.irrelevant == 1
    clusters = await clusters_by_main(client)
    assert list(clusters) == ["espresso machine for home"]
    assert clusters["espresso machine for home"]["isRanked"] is True


async def test_ranked_keywords_become_clusters(client, email, vendor):
    user_id, site, caller = await make_site(client, email)

    created = await create_from(user_id, site, caller, "ranked_keywords")

    assert created.candidates == 2
    assert created.noise == 1
    clusters = await clusters_by_main(client)
    assert list(clusters) == ["best espresso machine"]
    assert clusters["best espresso machine"]["isRanked"] is True


def test_seeds_are_required_only_for_the_seed_source():
    with pytest.raises(ValueError, match="seed"):
        CreateClustersRequest(source="seeds")
    assert CreateClustersRequest(source="search_console").seeds == []


async def create_from(user_id, site, caller, source):
    async with unit_of_work() as db:
        return await keyword_cluster_service.create_clusters(
            db, caller, user_id, site, CreateClustersRequest(source=source)
        )
