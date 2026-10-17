import pytest

from src.core.database import unit_of_work
from src.providers.registry import VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.serp_history.presence import presence
from src.seo.site_seo.competitor_repository import site_competitors
from tests.conftest import signup


def organic(rank: int, url: str) -> dict:
    return {"type": "organic", "rank_group": rank, "url": url, "domain": url.split("/")[2]}


def snapshot(day: str, results: list[tuple[int, str]]) -> dict:
    return {
        "datetime": f"{day} 08:00:00 +00:00",
        "items": [{"type": "people_also_ask", "rank_group": 1}]
        + [organic(rank, url) for rank, url in results],
    }


SNAPSHOTS = [
    snapshot(
        "2026-01-05",
        [(1, "https://rival.com/a"), (3, "https://flash.com/x"), (8, "https://www.example.com/e")],
    ),
    snapshot("2025-11-04", [(2, "https://rival.com/a"), (15, "https://deep.com/x")]),
    snapshot(
        "2026-03-02",
        [
            (1, "https://rival.com/b"),
            (4, "https://steady.com/s"),
            (6, "https://blog.example.com/e"),
        ],
    ),
    snapshot(
        "2026-06-01",
        [(3, "https://rival.com/a"), (5, "https://steady.com/s"), (4, "https://www.example.com/e")],
    ),
]


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        assert query["endpoint"] == ENDPOINTS["historical_serps"]
        body = {
            "status_code": 20000,
            "cost": 0.02,
            "tasks": [{"status_code": 20000, "cost": 0.02, "result": [{"items": SNAPSHOTS}]}],
        }
        return VendorResponse(body, 20_000)


@pytest.fixture
def vendor(monkeypatch):
    fake = FakeDataForSeo()
    monkeypatch.setattr(seo_data, "adapters", [fake])
    return fake


def test_consistent_domains_need_half_the_snapshots():
    ordered = sorted(SNAPSHOTS, key=lambda s: s["datetime"])
    consistent, sporadic, ours = presence(ordered, "example.com", 10, 0.5, {"rival.com"})
    assert [c.domain for c in consistent] == ["rival.com", "steady.com"]
    rival, steady = consistent
    assert (rival.appearances, rival.presence, rival.best_position) == (4, 1.0, 1)
    assert (rival.average_position, rival.latest_position, rival.saved) == (1.8, 3, True)
    assert rival.top_url == "https://rival.com/a"
    assert (steady.appearances, steady.average_position, steady.saved) == (2, 4.5, False)
    assert sporadic == 1
    assert ours is not None
    assert (ours.domain, ours.appearances, ours.best_position, ours.latest_position) == (
        "example.com",
        3,
        4,
        4,
    )


async def test_route_reads_twelve_months_once_and_marks_saved_competitors(client, email, vendor):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    site_id = r.json()["data"]["id"]
    user_id = (await client.get("/api/auth/me")).json()["data"]["id"]
    async with unit_of_work() as db:
        await site_competitors.add_many(db, user_id, site_id, {"rival.com": None})

    r = await client.post(
        "/api/v1/site/seo/serp-history",
        json={"keyword": "Espresso  Machine", "locationCode": 2826},
    )
    assert r.status_code == 200, r.text
    history = r.json()["data"]
    assert history["keyword"] == "espresso machine"
    assert history["locationCode"] == 2826
    assert history["snapshots"] == 4
    assert (history["firstDay"], history["lastDay"]) == ("2025-11-04", "2026-06-01")
    assert [c["domain"] for c in history["competitors"]] == ["rival.com", "steady.com"]
    assert history["competitors"][0]["saved"] is True
    assert history["sporadic"] == 1
    assert history["ours"]["appearances"] == 3

    [sent] = vendor.sent
    assert sent["task"]["keyword"] == "espresso machine"
    assert sent["task"]["date_from"].endswith("-01")

    r = await client.post(
        "/api/v1/site/seo/serp-history", json={"keyword": "espresso machine", "locationCode": 2826}
    )
    assert r.status_code == 200, r.text
    assert len(vendor.sent) == 1
