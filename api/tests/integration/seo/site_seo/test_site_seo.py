import pytest

from src.core.database import unit_of_work
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.market import ENGLISH_MARKETS, location_code, markets
from src.seo.site_seo.service import site_seo_service
from tests.conftest import signup
from tests.integration.seo.site_search.test_search_data import BATCH

BASE = "/api/v1/site/seo"


def envelope(items: list[dict]) -> dict:
    return {
        "status_code": 20000,
        "cost": 0.01,
        "tasks": [{"status_code": 20000, "cost": 0.01, "result": [{"items": items}]}],
    }


def referrer(domain: str, rank: int, backlinks: int, spam: int = 5) -> dict:
    return {
        "domain_intersection": {
            "1": {
                "target": domain,
                "rank": rank,
                "backlinks": backlinks,
                "backlinks_spam_score": spam,
            }
        },
        "summary": {"intersections_count": 1},
    }


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []
        self.referrers = {
            "rival.com": [referrer("blog.net", 400, 3), referrer("news.org", 700, 1)],
            "other.io": [referrer("blog.net", 400, 2), referrer("www.example.com", 900, 1)],
        }

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        endpoint, task = query["endpoint"], query["task"]
        if endpoint == ENDPOINTS["competitors"]:
            items = [
                {"domain": "example.com", "intersections": 999, "avg_position": 1},
                {"domain": "rival.com", "intersections": 120, "avg_position": 6.5},
                {"domain": "wikipedia.org", "intersections": 300, "avg_position": 9},
            ]
        elif endpoint == ENDPOINTS["serp_competitors"]:
            items = [
                {"domain": "www.rival.com", "visibility": 0.4, "avg_position": 5},
                {"domain": "other.io", "visibility": 0.2, "avg_position": 7},
            ]
        elif endpoint == ENDPOINTS["backlinks_domain_intersection"]:
            items = self.referrers[task["targets"]["1"]]
        else:
            raise AssertionError(endpoint)
        return VendorResponse(envelope(items), 10_000)


@pytest.fixture
def vendor(monkeypatch):
    fake = FakeDataForSeo()
    monkeypatch.setattr(seo_data, "adapters", [fake])
    return fake


async def make_site(client, email) -> tuple[str, str]:
    await signup(client, email)
    user_id = (await client.get("/api/auth/me")).json()["data"]["id"]
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    return user_id, r.json()["data"]["id"]


async def test_lists_start_empty_and_add_remove_by_domain(client, email):
    await make_site(client, email)

    r = await client.get(BASE)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["competitors"] == []

    r = await client.post(
        f"{BASE}/competitors/add",
        json={"items": ["https://www.Rival.com/pricing", "other.io", "rival.com"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["added"] == ["rival.com", "other.io"]
    assert r.json()["data"]["items"] == ["rival.com", "other.io"]

    r = await client.post(f"{BASE}/competitors/add", json={"items": ["rival.com", "third.dev"]})
    assert r.json()["data"]["added"] == ["third.dev"]
    assert r.json()["data"]["unchanged"] == ["rival.com"]

    r = await client.post(f"{BASE}/competitors/remove", json={"items": ["other.io", "nope.com"]})
    assert r.json()["data"]["removed"] == ["other.io"]
    assert r.json()["data"]["unchanged"] == ["nope.com"]

    r = await client.post(f"{BASE}/backlink_opportunities/add", json={"items": ["blog.net"]})
    assert r.json()["data"]["items"] == ["blog.net"]

    body = (await client.get(BASE)).json()["data"]
    assert body["competitors"] == ["rival.com", "third.dev"]
    assert body["backlinkOpportunities"] == ["blog.net"]


async def test_lists_reject_unknown_names_and_empty_items(client, email):
    await make_site(client, email)
    r = await client.post(f"{BASE}/rivals/add", json={"items": ["rival.com"]})
    assert r.status_code == 400
    r = await client.post(f"{BASE}/competitors/add", json={"items": ["", "  "]})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "Pass at least one domain."


async def test_find_competitors_merges_shared_keywords_with_search_console_serps(
    client, email, vendor
):
    user_id, site_id = await make_site(client, email)
    r = await client.post("/api/v1/site/search-data/rows", json=BATCH)
    assert r.status_code == 200, r.text
    await client.post(f"{BASE}/competitors/add", json={"items": ["other.io"]})

    async with unit_of_work() as db:
        found = await site_seo_service.find_competitors(
            db,
            Caller(user_id=user_id, site_id=site_id),
            site_id,
            "example.com",
            10,
            markets([], None),
        )

    assert found.sampled_queries == 2
    rows = {c.domain: c for c in found.competitors}
    assert "example.com" not in rows
    assert found.competitors[0].domain == "rival.com"
    assert rows["rival.com"].sources == ["shared_keywords", "search_console_serps"]
    assert rows["rival.com"].shared_keywords == 120 * len(ENGLISH_MARKETS)
    assert rows["rival.com"].avg_position == 5
    markets_asked = {
        q["task"]["location_code"] for q in vendor.sent if q["endpoint"] == ENDPOINTS["competitors"]
    }
    assert markets_asked == {location_code(c) for c in ENGLISH_MARKETS}
    assert rows["rival.com"].visibility == pytest.approx(0.4)
    assert rows["other.io"].saved is True
    assert rows["wikipedia.org"].sources == ["shared_keywords"]
    serp_task = next(q for q in vendor.sent if q["endpoint"] == ENDPOINTS["serp_competitors"])
    assert set(serp_task["task"]["keywords"]) == {"espresso machine", "coffee grinder"}


async def test_backlink_opportunities_rank_domains_linking_to_more_competitors(
    client, email, vendor
):
    user_id, site_id = await make_site(client, email)
    await client.post(f"{BASE}/competitors/add", json={"items": ["rival.com", "other.io"]})
    await client.post(f"{BASE}/backlink_opportunities/add", json={"items": ["news.org"]})

    async with unit_of_work() as db:
        found = await site_seo_service.find_backlink_opportunities(
            db, Caller(user_id=user_id, site_id=site_id), site_id, "example.com", None, 10
        )

    assert found.competitors == ["rival.com", "other.io"]
    assert [o.domain for o in found.opportunities] == ["blog.net", "news.org"]
    blog = found.opportunities[0]
    assert blog.links_to == ["rival.com", "other.io"]
    assert blog.backlinks_to_competitors == 5
    assert found.opportunities[1].saved is True
    gap_task = next(
        q for q in vendor.sent if q["endpoint"] == ENDPOINTS["backlinks_domain_intersection"]
    )
    assert gap_task["task"]["exclude_targets"] == ["example.com"]


async def test_backlink_opportunities_need_competitors(client, email, vendor):
    user_id, site_id = await make_site(client, email)
    async with unit_of_work() as db:
        with pytest.raises(Exception, match="No competitors"):
            await site_seo_service.find_backlink_opportunities(
                db, Caller(user_id=user_id, site_id=site_id), site_id, "example.com", None, 10
            )
