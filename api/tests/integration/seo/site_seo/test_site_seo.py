import pytest

from src.core.database import unit_of_work
from src.providers.registry import VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.site_seo.service import backlink_draft, site_seo_service
from tests.conftest import signup

BASE = "/api/v1/site/seo"


def envelope(result: dict) -> dict:
    return {
        "status_code": 20000,
        "cost": 0.01,
        "tasks": [{"status_code": 20000, "cost": 0.01, "result": [result]}],
    }


def link(domain_from: str, target: str, **overrides) -> dict:
    return {
        "type": "backlink",
        "domain_from": domain_from,
        "url_from": f"https://{domain_from}/espresso-guide",
        "url_to": f"https://{target}/",
        "anchor": "espresso machines",
        "item_type": "anchor",
        "dofollow": True,
        "attributes": None,
        "semantic_location": "article",
        "group_count": 1,
        "is_lost": False,
        "is_broken": False,
        "first_seen": "2025-04-01 08:00:00 +00:00",
        "last_seen": "2026-10-01 08:00:00 +00:00",
        "backlink_spam_score": 5,
        "domain_from_rank": 400,
        "page_from_rank": 200,
        "domain_from_is_ip": False,
        "domain_from_platform_type": ["blogs"],
        "domain_from_country": "GB",
        "page_from_title": "The best espresso machines",
        "page_from_language": "en",
        "page_from_status_code": 200,
        "page_from_external_links": 12,
        **overrides,
    }


BACKLINKS = {
    "rival.com": [
        link("blog.net", "rival.com"),
        link("news.org", "rival.com", domain_from_rank=700),
        link("already.org", "rival.com"),
        link("spammy.xyz", "rival.com", backlink_spam_score=80),
        link("other.io", "rival.com"),
    ],
    "other.io": [
        link("news.org", "other.io", domain_from_rank=700),
        link("paid.blog", "other.io", attributes=["sponsored"]),
    ],
    "example.com": [link("already.org", "example.com")],
}

RANKS = {"rival.com": 520, "other.io": 310}


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        endpoint, task = query["endpoint"], query["task"]
        if endpoint == ENDPOINTS["backlinks"]:
            body = {"target": task["target"], "items": BACKLINKS.get(task["target"], [])}
        elif endpoint == ENDPOINTS["bulk_ranks"]:
            body = {"items": [{"target": t, "rank": RANKS.get(t, 0)} for t in task["targets"]]}
        elif endpoint == ENDPOINTS["bulk_spam_score"]:
            body = {"items": [{"target": t, "spam_score": 3} for t in task["targets"]]}
        else:
            raise AssertionError(endpoint)
        return VendorResponse(envelope(body), 10_000)


@pytest.fixture
def vendor(monkeypatch):
    fake = FakeDataForSeo()
    monkeypatch.setattr(seo_data, "adapters", [fake])
    return fake


async def make_site(client, email) -> None:
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text


def sent_to(vendor, endpoint: str) -> list[str]:
    return [q["task"].get("target") for q in vendor.sent if q["endpoint"] == ENDPOINTS[endpoint]]


async def add_and_fetch(client, domains: list[str]) -> None:
    r = await client.post(f"{BASE}/competitors", json={"domains": domains})
    assert r.status_code == 200, r.text
    r = await client.post(f"{BASE}/backlinks/fetch", json={"domains": domains})
    assert r.status_code == 200, r.text


async def test_adding_a_competitor_saves_its_rank_but_fetches_no_backlinks(client, email, vendor):
    await make_site(client, email)

    r = await client.post(
        f"{BASE}/competitors", json={"domains": ["https://www.Rival.com/pricing", "example.com"]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["added"] == ["rival.com"]
    assert r.json()["data"]["unchanged"] == ["example.com"]
    assert sent_to(vendor, "backlinks") == []

    r = await client.post(f"{BASE}/competitors", json={"domains": ["other.io", "rival.com"]})
    assert r.json()["data"]["added"] == ["other.io"]
    rows = {c["domain"]: c for c in (await client.get(f"{BASE}/competitors")).json()["data"]}
    assert rows["rival.com"]["domainRank"] == 520
    assert (rows["rival.com"]["backlinks"], rows["rival.com"].get("backlinksFetchedAt")) == (
        0,
        None,
    )


async def test_backlinks_are_fetched_only_for_the_competitors_named_and_ours_once(
    client, email, vendor
):
    await make_site(client, email)
    await client.post(f"{BASE}/competitors", json={"domains": ["rival.com", "other.io"]})

    r = await client.post(f"{BASE}/backlinks/fetch", json={"domains": ["rival.com", "nope.com"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["fetched"] == [
        {"domain": "rival.com", "backlinks": 4},
        {"domain": "example.com", "backlinks": 1},
    ]
    assert r.json()["data"]["notSaved"] == ["nope.com"]
    assert sorted(sent_to(vendor, "backlinks")) == ["example.com", "rival.com"]
    assert len(sent_to(vendor, "bulk_spam_score")) == 1

    r = await client.post(f"{BASE}/backlinks/fetch", json={"domains": ["other.io"]})
    assert r.json()["data"]["fetched"] == [{"domain": "other.io", "backlinks": 1}]
    assert sorted(sent_to(vendor, "backlinks")) == ["example.com", "other.io", "rival.com"]

    rows = {c["domain"]: c for c in (await client.get(f"{BASE}/competitors")).json()["data"]}
    assert (rows["rival.com"]["backlinks"], rows["other.io"]["backlinks"]) == (4, 1)
    assert rows["other.io"]["backlinksFetchedAt"] is not None


async def test_opportunities_are_links_to_competitors_that_skip_us(client, email, vendor):
    await make_site(client, email)
    await add_and_fetch(client, ["rival.com", "other.io"])

    r = await client.get(f"{BASE}/backlink-opportunities")
    assert r.status_code == 200, r.text
    found = r.json()["data"]
    assert [o["domain"] for o in found] == ["news.org", "blog.net"]
    assert found[0]["linksTo"] == ["other.io", "rival.com"]
    assert found[0]["domainRank"] == 700
    assert found[0]["exampleUrl"].startswith("https://news.org/")
    assert r.json()["pagination"]["total"] == 2

    r = await client.post(
        f"{BASE}/backlink-opportunities/dismiss", json={"domains": ["blog.net", "nobody.com"]}
    )
    assert r.json()["data"] == {"dismissed": ["blog.net"], "notFound": ["nobody.com"]}
    r = await client.get(f"{BASE}/backlink-opportunities")
    assert [o["domain"] for o in r.json()["data"]] == ["news.org"]


async def test_removing_a_competitor_drops_its_backlinks(client, email, vendor):
    await make_site(client, email)
    await add_and_fetch(client, ["rival.com", "other.io"])
    rows = {c["domain"]: c for c in (await client.get(f"{BASE}/competitors")).json()["data"]}

    r = await client.delete(f"{BASE}/competitors/{rows['other.io']['id']}")
    assert r.status_code == 204
    r = await client.get(f"{BASE}/backlink-opportunities")
    found = {o["domain"]: o["linksTo"] for o in r.json()["data"]}
    assert found == {
        "news.org": ["rival.com"],
        "blog.net": ["rival.com"],
        "other.io": ["rival.com"],
    }
    r = await client.delete(f"{BASE}/competitors/scmp_missing")
    assert r.status_code == 404


async def test_domains_must_be_given(client, email, vendor):
    await make_site(client, email)
    r = await client.post(f"{BASE}/competitors", json={"domains": ["   "]})
    assert r.status_code == 400
    assert vendor.sent == []


def draft(**overrides):
    return backlink_draft(link("blog.net", "rival.com", **overrides), "rival.com", {}, set())


def test_spam_paid_and_weak_links_are_never_kept():
    assert draft() is not None
    for bad in (
        {"backlink_spam_score": None},
        {"backlink_spam_score": 45},
        {"page_from_external_links": 400},
        {"domain_from_is_ip": True},
        {"attributes": ["nofollow", "sponsored"]},
        {"url_from": "https://blog.net/write-for-us"},
        {"page_from_title": "Sponsored: our partners"},
        {"group_count": 60},
        {"domain_from_rank": 40},
        {"item_type": "redirect"},
        {"page_from_status_code": 404},
    ):
        assert draft(**bad) is None, bad
    assert draft(dofollow=False, attributes=["nofollow"]) is not None
    spammy_domain = backlink_draft(
        link("blog.net", "rival.com"), "rival.com", {"blog.net": 70}, set()
    )
    assert spammy_domain is None


async def test_removing_a_backlink_domain_deletes_all_its_rows(client, email, vendor):
    await make_site(client, email)
    await add_and_fetch(client, ["rival.com", "other.io"])
    site_id = (await client.get("/api/v1/sites")).json()["data"][0]["id"]

    async with unit_of_work() as db:
        removed = await site_seo_service.remove_backlink_domain(db, site_id, "news.org")
    assert removed.backlinks_removed == 2

    r = await client.get(f"{BASE}/backlink-opportunities")
    assert [o["domain"] for o in r.json()["data"]] == ["blog.net"]
    rows = {c["domain"]: c for c in (await client.get(f"{BASE}/competitors")).json()["data"]}
    assert (rows["rival.com"]["backlinks"], rows["other.io"]["backlinks"]) == (3, 0)
