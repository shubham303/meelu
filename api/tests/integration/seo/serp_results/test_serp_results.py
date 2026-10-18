import pytest

from src.core.database import unit_of_work
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.keyword_clusters.repository import seo_keyword_clusters
from src.seo.keyword_clusters.schemas import ClusterDraft
from src.seo.keyword_clusters.service import keyword_cluster_service
from src.seo.serp_results.poisoning import organic, rated, sibling_check, verdict
from src.sites.service import site_service
from tests.conftest import signup

REAL = ["https://moz.com/ai", "https://ahrefs.com/ai", "https://semrush.com/ai"]
SPAM = ["https://ai-seo-1.xyz/a", "https://ai-seo-2.xyz/b", "https://ai-seo-3.xyz/c"]
RANKS = {
    **{url: (300, 700) for url in REAL},
    **{url: (2, 10) for url in SPAM},
    "https://www.example.com/ai": (5, 40),
}


def page(urls: list[str]) -> dict:
    return {
        "datetime": "2026-10-16 08:00:00 +00:00",
        "items": [
            {"type": "organic", "rank_group": seat, "url": url, "domain": url.split("/")[2]}
            for seat, url in enumerate(urls, start=1)
        ],
    }


SERPS = {
    "seo with ai": page([*SPAM, "https://www.example.com/ai"]),
    "ai seo": page(REAL),
    "ai seo tools": page(REAL[::-1]),
}


def envelope(result: dict) -> dict:
    return {
        "status_code": 20000,
        "cost": 0.002,
        "tasks": [{"status_code": 20000, "cost": 0.002, "result": [result]}],
    }


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        endpoint, task = query["endpoint"], query["task"]
        if endpoint == ENDPOINTS["serp"]:
            body = envelope(SERPS[task["keyword"]])
        elif endpoint == ENDPOINTS["bulk_pages_summary"]:
            body = envelope(
                {
                    "items": [
                        {"url": u, "rank": RANKS[u][0], "main_domain_rank": RANKS[u][1]}
                        for u in task["targets"]
                    ]
                }
            )
        else:
            raise AssertionError(endpoint)
        return VendorResponse(body, 2_000)


@pytest.fixture
def vendor(monkeypatch):
    fake = FakeDataForSeo()
    monkeypatch.setattr(seo_data, "adapters", [fake])
    return fake


def summary(urls: list[str]) -> dict[str, dict]:
    return {u: {"rank": RANKS[u][0], "main_domain_rank": RANKS[u][1]} for u in urls}


def test_each_result_keeps_what_the_searcher_sees():
    item = {
        "type": "organic",
        "rank_group": 1,
        "url": "https://shop.example/espresso",
        "domain": "shop.example",
        "title": "Espresso machines",
        "description": "Buy espresso machines with free delivery.",
        "breadcrumb": "https://shop.example › kitchen › espresso",
        "website_name": "Shop",
        "highlighted": ["espresso machines", None],
        "timestamp": "2026-09-01 00:00:00 +00:00",
        "rating": {"rating_type": "Max5", "value": 4.6, "votes_count": 212, "rating_max": 5},
        "price": {"current": 199.0, "currency": "GBP", "displayed_price": "£199.00"},
        "is_featured_snippet": True,
        "is_video": False,
    }
    [row] = organic({"items": [item]}, 10)
    assert row == {
        "position": 1,
        "url": "https://shop.example/espresso",
        "domain": "shop.example",
        "title": "Espresso machines",
        "description": "Buy espresso machines with free delivery.",
        "breadcrumb": "https://shop.example › kitchen › espresso",
        "website_name": "Shop",
        "highlighted": ["espresso machines"],
        "date": "2026-09-01 00:00:00 +00:00",
        "rating": 4.6,
        "rating_votes": 212,
        "price": "£199.00",
        "featured_snippet": True,
        "video": False,
    }
    [bare] = organic(page(["https://moz.com/ai"]), 10)
    assert (bare["description"], bare["rating"], bare["price"], bare["highlighted"]) == (
        None,
        None,
        None,
        [],
    )


def test_strong_top_results_that_match_the_cluster_are_clean():
    main = organic(page(REAL), 10)
    results = rated(main, summary(REAL), "example.com")
    found, weak_top, overlap, reasons = verdict(
        results, [sibling_check("ai seo tools", main, organic(page(REAL[::-1]), 10))]
    )
    assert (found, weak_top, overlap, reasons) == ("clean", 0, 1.0, [])


def test_weak_top_results_alone_are_suspect_and_our_site_never_counts_as_weak():
    urls = [SPAM[0], "https://www.example.com/ai", SPAM[1], REAL[0]]
    results = rated(organic(page(urls), 10), summary(urls), "example.com")
    assert [r.weak for r in results] == [True, False, True, False]
    assert results[1].ours
    found, weak_top, overlap, _ = verdict(results, [])
    assert (found, weak_top, overlap) == ("suspect", 2, None)


async def test_weak_results_out_of_line_with_the_cluster_are_poisoned(client, email, vendor):
    await signup(client, email)
    user_id = (await client.get("/api/auth/me")).json()["data"]["id"]
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    site_id = r.json()["data"]["id"]
    async with unit_of_work() as db:
        await seo_keyword_clusters.upsert_many(
            db,
            user_id,
            site_id,
            [
                ClusterDraft(
                    main_keyword="ai seo",
                    keywords=["ai seo", "seo with ai", "ai seo tools"],
                    core_keyword=None,
                    seeds=["ai seo"],
                    location_code=2840,
                    language_code="en",
                    volume=500,
                )
            ],
        )

    r = await client.post(
        "/api/v1/site/seo/serp-results", json={"keyword": "SEO with AI", "locationCode": 2840}
    )
    assert r.status_code == 200, r.text
    found = r.json()["data"]
    assert found["verdict"] == "poisoned"
    assert "fake results" in found["message"]
    assert found["weakTop"] == 3
    assert [s["keyword"] for s in found["siblings"]] == ["ai seo", "ai seo tools"]
    assert found["siblingOverlap"] == 0.0
    assert found["results"][3]["ours"] is True
    assert found["results"][0]["pageRank"] == 2
    assert len(found["reasons"]) == 2
    assert len(vendor.sent) == 4

    r = await client.post(
        "/api/v1/site/seo/serp-results",
        json={"keyword": "seo with ai", "locationCode": 2840, "useCache": True},
    )
    assert r.status_code == 200, r.text
    assert len(vendor.sent) == 4

    r = await client.post(
        "/api/v1/site/seo/serp-results", json={"keyword": "seo with ai", "locationCode": 2840}
    )
    assert r.status_code == 200, r.text
    assert [q["endpoint"] for q in vendor.sent[4:]] == [ENDPOINTS["serp"]] * 3


async def test_a_cluster_with_a_poisoned_results_page_is_not_scored(client, email, vendor):
    await signup(client, email)
    user_id = (await client.get("/api/auth/me")).json()["data"]["id"]
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    site_id = r.json()["data"]["id"]
    async with unit_of_work() as db:
        [saved] = await seo_keyword_clusters.upsert_many(
            db,
            user_id,
            site_id,
            [
                ClusterDraft(
                    main_keyword="seo with ai",
                    keywords=["seo with ai", "ai seo", "ai seo tools"],
                    core_keyword=None,
                    seeds=["seo with ai"],
                    location_code=2840,
                    language_code="en",
                    volume=500,
                )
            ],
        )
    async with unit_of_work() as db:
        site = await site_service.get(db, user_id, site_id)
        computed = await keyword_cluster_service.compute_metrics(
            db, Caller(user_id=user_id, site_id=site_id), site, [saved.id]
        )

    assert (computed.computed, computed.failed, computed.poisoned) == (0, [], ["seo with ai"])
    r = await client.get("/api/v1/site/seo/clusters")
    [cluster] = r.json()["data"]
    assert cluster["serpVerdict"] == "poisoned"
    assert "winnability" not in cluster
    assert cluster["climb"] == []
    assert cluster["metricsAt"]
