import asyncio

import pytest
from sqlalchemy import select

from src.agent.security import bootstrap
from src.core.database import unit_of_work
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.keyword_tracking.models.seo_volume_history import SeoVolumeHistory
from src.seo.keyword_tracking.schemas import TrackKeywordsRequest
from src.seo.keyword_tracking.service import keyword_tracking_service
from src.seo.market import ENGLISH_MARKETS, markets
from tests.conftest import signup


def envelope(items: list[dict]) -> dict:
    return {
        "status_code": 20000,
        "cost": 0.01,
        "tasks": [{"status_code": 20000, "cost": 0.01, "result": [{"items": items}]}],
    }


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        endpoint, task = query["endpoint"], query["task"]
        if endpoint == ENDPOINTS["keyword_overview"]:
            body = envelope(
                [
                    {
                        "keyword": k,
                        "keyword_info": {
                            "cpc": 2.5,
                            "competition": 0.3,
                            "monthly_searches": [
                                {"year": 2026, "month": 8, "search_volume": 1000},
                                {"year": 2026, "month": 7, "search_volume": 900},
                            ],
                        },
                        "clickstream_keyword_info": {
                            "monthly_searches": [
                                {"year": 2026, "month": 8, "search_volume": 120},
                                {"year": 2026, "month": 9, "search_volume": 140},
                            ]
                        },
                    }
                    for k in task["keywords"]
                    if k != "nothing here"
                ]
            )
        else:
            raise AssertionError(endpoint)
        return VendorResponse(body, 10_000)


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


def gsc_row(query: str, page: str, country: str, impressions: int, position: float) -> dict:
    return {
        "query": query,
        "page": page,
        "device": "DESKTOP",
        "country": country,
        "clicks": 1,
        "impressions": impressions,
        "position": position,
    }


async def test_tracked_overview_reads_our_rank_from_search_console(client, email, vendor):
    user_id, site_id = await make_site(client, email)
    async with unit_of_work() as db:
        await keyword_tracking_service.track_volumes(
            db,
            Caller(user_id=user_id, site_id=site_id),
            user_id,
            site_id,
            TrackKeywordsRequest(keywords=["espresso machine"]),
            markets(["GB"], "en"),
        )

    espresso = "https://www.example.com/espresso"
    other = "https://www.example.com/other"
    r = await client.post(
        "/api/v1/site/search-data/rows",
        json={
            "days": [
                {
                    "day": "2026-08-10",
                    "rows": [gsc_row("espresso machine", espresso, "gbr", 100, 6)],
                },
                {
                    "day": "2026-09-10",
                    "rows": [
                        gsc_row("Espresso  Machine", espresso, "gbr", 300, 4),
                        gsc_row("espresso machine", other, "gbr", 100, 8),
                        gsc_row("espresso machine", espresso, "usa", 1000, 1),
                    ],
                },
            ]
        },
    )
    assert r.status_code == 200, r.text

    r = await client.get("/api/v1/site/seo/tracked", params={"locationCode": 2826})
    assert r.status_code == 200, r.text
    overview = r.json()["data"]
    assert overview["locationCode"] == 2826
    assert {"locationCode": 2826, "languageCode": "en", "country": "GB"} in overview["markets"]
    [tracked] = overview["keywords"]
    assert tracked["keyword"] == "espresso machine"
    assert tracked["position"] == 5.0
    assert tracked["previousPosition"] == 6.0
    assert tracked["change"] == 1.0
    assert tracked["url"] == espresso
    history = dict(zip(overview["months"], tracked["history"], strict=True))
    assert history["2026-08-01"] == 6.0 and history["2026-09-01"] == 5.0
    assert overview["stats"] == {"tracked": 1, "topTen": 1, "moved": 1, "notRanking": 0}


async def test_volumes_merge_ads_with_clickstream_from_one_overview(client, email, vendor):
    user_id, site_id = await make_site(client, email)
    async with unit_of_work() as db:
        tracked = await keyword_tracking_service.track_volumes(
            db,
            Caller(user_id=user_id, site_id=site_id),
            user_id,
            site_id,
            TrackKeywordsRequest(keywords=["espresso machine", "nothing here"]),
            markets([], None),
        )
    assert tracked.months == 3
    assert tracked.rows == 3 * len(ENGLISH_MARKETS)
    assert tracked.without_data == ["nothing here"]

    async with unit_of_work() as db:
        rows = (
            await db.scalars(
                select(SeoVolumeHistory)
                .where(SeoVolumeHistory.site_id == site_id, SeoVolumeHistory.location_code == 2036)
                .order_by(SeoVolumeHistory.month)
            )
        ).all()
    assert [(r.month.month, r.search_volume, r.clickstream_volume) for r in rows] == [
        (7, 900, None),
        (8, 1000, 120),
        (9, None, 140),
    ]
    assert rows[1].cpc == pytest.approx(2.5)
    assert rows[0].cpc is None and rows[2].cpc is None
    assert {q["endpoint"] for q in vendor.sent} == {ENDPOINTS["keyword_overview"]}
    assert len(vendor.sent) == len(ENGLISH_MARKETS)


async def test_the_agent_can_query_the_volume_history():
    granted = (await asyncio.to_thread(bootstrap)).granted
    assert {"seo_volume_history", "site_competitors", "site_backlinks"} <= set(granted)
    assert "seo_rank_history" not in granted


async def test_track_volumes_route_covers_the_site_markets(client, email, vendor):
    await make_site(client, email)
    r = await client.post(
        "/api/v1/site/seo/tracked/volumes", json={"keywords": ["Espresso Machine"]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["rows"] == 3 * len(ENGLISH_MARKETS)

    r = await client.get("/api/v1/site/seo/tracked")
    [tracked] = r.json()["data"]["keywords"]
    assert tracked["keyword"] == "espresso machine"
    assert "position" not in tracked
