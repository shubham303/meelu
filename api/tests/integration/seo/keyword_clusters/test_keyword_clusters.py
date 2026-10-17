import asyncio
import re
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import delete

from src.core.database import unit_of_work
from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.models.provider_cache import ProviderCache
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.keyword_clusters.schemas import (
    ClustersDeleteRequest,
    CompetitorClustersRequest,
    KeywordsClusterRequest,
    SearchConsoleClustersRequest,
    SeedClustersRequest,
)
from src.seo.keyword_clusters.service import keyword_cluster_service, rows_per_competitor
from src.seo.site_seo.competitor_repository import site_competitors
from src.sites.service import site_service
from tests.conftest import signup

FACTS = {
    "espresso machine": (10000, 5000, "espresso machine"),
    "best espresso machine": (8000, 3000, "espresso machine"),
    "espresso machine for home": (2000, 900, "espresso machine"),
    "cheap espresso machines": (900, 150, "espresso machine"),
    "espresso machine repair jobs": (500, 300, None),
    "best home espresso machine": (300, 120, "espresso machine"),
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
        self.competitor_keywords: list[str] = []

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
            body = envelope(
                [
                    {
                        "keyword_data": {"keyword": k},
                        "ranked_serp_element": {
                            "serp_item": {"rank_group": 5, "url": f"https://{task['target']}/x"}
                        },
                    }
                    for k in self.competitor_keywords
                ]
            )
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
            if text.endswith("a brand search?"):
                pick = "yes" if "home" in text else "no"
            elif text.startswith("Is "):
                pick = "no" if "jobs" in text else "yes"
            elif text.startswith("What does a person"):
                pick = "commercial" if "home" in text else "informational"
            elif text.startswith("How close is"):
                pick = "warm" if "home" in text else "cold"
            elif text.startswith("Does a person"):
                asked = re.findall(r'"([^"]+)"', text)[0]
                pick = "yes" if asked.startswith("best ") else "no"
            else:
                seat = int(re.findall(r"result (\d+)", text)[0]) - 1
                pick = "none" if "Login" in (state[f"result {seat + 1}"]["title"] or "") else "full"
            answers[key] = {"type": "choice", "choice": pick, "confidence": 0.9}
        return VendorResponse({"model": "fake", "answers": answers}, 100)


def overviewed(vendor: FakeDataForSeo) -> set[str]:
    return {
        k
        for q in vendor.sent
        if q["endpoint"] == ENDPOINTS["keyword_overview"]
        for k in q["task"]["keywords"]
    }


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


async def search_console(client, queries):
    day = (datetime.now(UTC).date() - timedelta(days=4)).isoformat()
    rows = [
        {
            "query": q,
            "page": "https://example.com/p",
            "device": "DESKTOP",
            "country": "usa",
            "clicks": 1,
            "impressions": 40,
            "position": 12,
        }
        for q in queries
    ]
    r = await client.post(
        "/api/v1/site/search-data/rows", json={"days": [{"day": day, "rows": rows}]}
    )
    assert r.status_code == 200, r.text


async def create(user_id, site, caller, **body):
    async with unit_of_work() as db:
        return await asyncio.wait_for(
            keyword_cluster_service.from_seeds(
                db, caller, user_id, site, SeedClustersRequest(seeds=["Espresso Machine"], **body)
            ),
            timeout=30,
        )


async def test_relevance_then_noise_then_same_results_split(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    await search_console(client, ["best espresso machine"])

    created = await create(user_id, site, caller)

    assert not any(q["endpoint"] == ENDPOINTS["ranked_keywords"] for q in vendor.sent)
    assert created == ["espresso machine", "espresso machine for home"]
    overview = next(q for q in vendor.sent if q["endpoint"] == ENDPOINTS["keyword_overview"])
    assert overview["task"]["location_code"] == 2826
    assert "espresso machine repair jobs" not in overviewed(vendor)

    r = await client.get("/api/v1/site/seo/clusters", params={"search": "best"})
    assert r.status_code == 200, r.text
    [cluster] = r.json()["data"]
    assert cluster["mainKeyword"] == "espresso machine"
    assert cluster["keywords"] == ["espresso machine", "best espresso machine"]
    assert cluster["coreKeyword"] == "espresso machine"
    assert cluster["isRanked"] is True
    assert cluster["competitors"] == []
    labels = {
        main: (c["intent"], c["importance"], c["isBrandKeyword"])
        for main, c in (await clusters_by_main(client)).items()
    }
    assert labels == {
        "espresso machine": ("informational", "cold", False),
        "espresso machine for home": ("commercial", "warm", True),
    }

    assert await create(user_id, site, caller) == []


async def test_a_hard_minimum_replaces_the_relative_floor(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    assert await create(user_id, site, caller, min_volume=1000) == ["espresso machine"]


def rival(seat: int, tag: str) -> str:
    return f"https://{tag}{seat}.com/espresso"


async def score(client, email, vendor, rival_rank: int, our_domain_rank: int, tag: str):
    user_id, site, caller = await make_site(client, email)
    await search_console(client, ["best espresso machine"])
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
    assert computed.computed == 1 and computed.failed == [] and computed.poisoned == []
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
    cluster = await score(client, email, vendor, rival_rank=60, our_domain_rank=1000, tag="weak")
    assert cluster["winnability"] > 70
    assert cluster["likelyPosition"] <= 3


async def test_clusters_scored_together_share_one_page_rank_request(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    assert len(await create(user_id, site, caller)) == 2
    vendor.serp_results = [(rival(s, "shared"), f"Guide {s}") for s in range(1, 11)]
    vendor.ranks = {rival(s, "shared"): (60, 60) for s in range(1, 11)}
    async with unit_of_work() as db:
        await db.execute(
            delete(ProviderCache).where(
                ProviderCache.capability.in_(["serp.organic", "backlinks.pages_summary"])
            )
        )
    vendor.sent.clear()

    async with unit_of_work() as db:
        computed = await asyncio.wait_for(
            keyword_cluster_service.compute_metrics(db, caller, site, None, 10), timeout=30
        )

    assert computed.computed == 2
    summaries = [q for q in vendor.sent if q["endpoint"] == ENDPOINTS["bulk_pages_summary"]]
    assert len(summaries) == 1
    assert "https://example.com/" in summaries[0]["task"]["targets"]


async def clusters_by_main(client) -> dict[str, dict]:
    r = await client.get("/api/v1/site/seo/clusters", params={"page_size": 50})
    assert r.status_code == 200, r.text
    return {c["mainKeyword"]: c for c in r.json()["data"]}


async def test_search_console_queries_become_clusters_we_rank_for(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    await search_console(client, ["espresso machine for home", "espresso machine repair jobs"])

    async with unit_of_work() as db:
        created = await keyword_cluster_service.from_search_console(
            db, caller, user_id, site, SearchConsoleClustersRequest()
        )

    assert created == ["espresso machine for home"]
    assert {q["endpoint"] for q in vendor.sent} == {ENDPOINTS["keyword_overview"]}
    clusters = await clusters_by_main(client)
    assert list(clusters) == ["espresso machine for home"]
    assert clusters["espresso machine for home"]["isRanked"] is True


async def add(user_id, site, caller, *keywords):
    async with unit_of_work() as db:
        return await asyncio.wait_for(
            keyword_cluster_service.add_keywords(
                db, caller, user_id, site, KeywordsClusterRequest(keywords=list(keywords))
            ),
            timeout=30,
        )


async def test_a_keyword_joins_the_cluster_of_its_core(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    await create(user_id, site, caller)

    placed = await add(user_id, site, caller, "Best Home Espresso Machine", "espresso machine")

    clusters = await clusters_by_main(client)
    core = clusters["espresso machine"]
    assert placed == [
        ("best home espresso machine", core["id"]),
        ("espresso machine", core["id"]),
    ]
    assert set(core["keywords"]) == {
        "espresso machine",
        "best espresso machine",
        "best home espresso machine",
    }
    assert core["volume"] == 8120

    sent = len(vendor.sent)
    assert await add(user_id, site, caller, "best home espresso machine") == [
        ("best home espresso machine", core["id"])
    ]
    assert len(vendor.sent) == sent


async def test_a_keyword_on_an_empty_list_clusters_its_core_too(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    await search_console(client, ["cheap espresso machines"])

    placed = await add(user_id, site, caller, "cheap espresso machines")

    clusters = await clusters_by_main(client)
    own = clusters["cheap espresso machines"]
    assert placed == [("cheap espresso machines", own["id"])]
    assert own["keywords"] == ["cheap espresso machines"]
    assert set(clusters) == {"espresso machine", "cheap espresso machines"}
    assert clusters["cheap espresso machines"]["isRanked"] is True
    assert clusters["espresso machine"]["isRanked"] is False


async def test_removing_keywords_lowers_the_cluster_volume(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    await create(user_id, site, caller)
    await add(user_id, site, caller, "best home espresso machine")
    cluster = (await clusters_by_main(client))["espresso machine"]
    url = f"/api/v1/site/seo/clusters/{cluster['id']}/keywords"

    r = await client.delete(url, params={"keyword": ["best home espresso machine", "milk frother"]})
    assert r.status_code == 404
    assert "milk frother" in r.text
    r = await client.delete(url, params={"keyword": ["best espresso machine", "espresso machine"]})
    assert r.status_code == 409
    assert (await clusters_by_main(client))["espresso machine"]["volume"] == 8120

    r = await client.delete(
        url, params={"keyword": ["Best Home Espresso Machine", "best espresso machine"]}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["keywords"] == ["espresso machine"]
    assert body["volume"] == 5000


async def test_clusters_are_deleted_by_ids_and_by_keywords_in_them(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    await create(user_id, site, caller)
    clusters = await clusters_by_main(client)
    assert {"espresso machine", "espresso machine for home"} <= set(clusters)
    target = clusters["espresso machine for home"]["id"]

    async with unit_of_work() as db:
        result = await keyword_cluster_service.delete_many(
            db,
            site,
            ClustersDeleteRequest(
                cluster_ids=[target, "kcl_missing"],
                keywords=["Best Espresso Machine", "espresso machine", "milk frother"],
            ),
        )

    assert {d.main_keyword for d in result.deleted} == {
        "espresso machine",
        "espresso machine for home",
    }
    assert result.missing_ids == ["kcl_missing"]
    assert result.unclustered_keywords == ["milk frother"]
    remaining = await clusters_by_main(client)
    assert "espresso machine" not in remaining
    assert "espresso machine for home" not in remaining


def test_deleting_clusters_needs_an_id_or_a_keyword():
    with pytest.raises(ValueError, match="cluster ids or keywords"):
        ClustersDeleteRequest(cluster_ids=[" "], keywords=["  "])


async def test_competitor_keywords_we_get_no_impressions_for_become_single_clusters(
    client, email, vendor
):
    user_id, site, caller = await make_site(client, email)
    await search_console(client, ["best espresso machine"])
    vendor.competitor_keywords = [
        "Espresso Machine For Home",
        "best espresso machine",
        "cheap espresso machines",
        "espresso machine repair jobs",
        "best home espresso machine",
    ]
    async with unit_of_work() as db:
        await site_competitors.add_many(
            db, user_id, site.id, {"rival.example": None, "other.example": None}
        )

    async with unit_of_work() as db:
        created = await keyword_cluster_service.from_competitors(
            db, caller, user_id, site, CompetitorClustersRequest()
        )

    assert created == ["espresso machine for home"]
    assert {q["endpoint"] for q in vendor.sent} == {
        ENDPOINTS["ranked_keywords"],
        ENDPOINTS["keyword_overview"],
    }
    assert "espresso machine repair jobs" not in overviewed(vendor)
    pulls = {
        q["task"]["target"]: q["task"]["limit"]
        for q in vendor.sent
        if q["endpoint"] == ENDPOINTS["ranked_keywords"]
    }
    assert pulls == {"rival.example": 200, "other.example": 200}
    clusters = await clusters_by_main(client)
    assert list(clusters) == ["espresso machine for home"]
    assert clusters["espresso machine for home"]["keywords"] == ["espresso machine for home"]
    assert clusters["espresso machine for home"]["volume"] == 900


def test_competitor_rows_scale_with_the_limit_and_split_across_competitors():
    assert rows_per_competitor(100, 2) == 200
    assert rows_per_competitor(100, 10) == 100
    assert rows_per_competitor(100, 1) == 400
    assert rows_per_competitor(500, 1) == 1000


async def test_competitor_clusters_need_saved_competitors(client, email, vendor):
    user_id, site, caller = await make_site(client, email)
    async with unit_of_work() as db:
        with pytest.raises(HTTPException) as refused:
            await keyword_cluster_service.from_competitors(
                db, caller, user_id, site, CompetitorClustersRequest()
            )
    assert refused.value.status_code == 409
    assert vendor.sent == []


def test_competitor_clusters_are_capped_at_a_hundred():
    with pytest.raises(ValueError):
        CompetitorClustersRequest(limit=101)


def test_competitor_lookback_defaults_to_28_days_and_is_capped_at_180():
    assert CompetitorClustersRequest().lookback == 28
    assert CompetitorClustersRequest(lookback=180).lookback == 180
    with pytest.raises(ValueError):
        CompetitorClustersRequest(lookback=181)


def test_keywords_to_add_need_one_and_are_capped():
    with pytest.raises(ValueError, match="keyword"):
        KeywordsClusterRequest(keywords=["  "])
    with pytest.raises(ValueError, match="50"):
        KeywordsClusterRequest(keywords=[f"keyword {n}" for n in range(51)])


def test_seed_clusters_need_a_seed():
    with pytest.raises(ValueError, match="seed"):
        SeedClustersRequest(seeds=[])
    with pytest.raises(ValueError, match="seed"):
        SeedClustersRequest(seeds=["  "])
