import asyncio
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from src.agent.security import bootstrap
from src.core.database import unit_of_work
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from src.seo.keyword_tracking.models.seo_rank_history import SeoRankHistory
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


def organic(rank: int, url: str, domain: str) -> dict:
    return {
        "type": "organic",
        "rank_group": rank,
        "rank_absolute": rank + 1,
        "url": url,
        "domain": domain,
        "title": url,
    }


def snapshot(day: str, ours_at: int | None) -> dict:
    items = [
        {"type": "people_also_ask", "rank_group": 1},
        organic(1, "https://rival.com/a", "rival.com"),
    ]
    if ours_at:
        items.append(organic(ours_at, "https://www.example.com/espresso", "www.example.com"))
    items.append(organic(40, "https://deep.com/x", "deep.com"))
    return {"datetime": f"{day} 08:00:00 +00:00", "items": items}


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        endpoint, task = query["endpoint"], query["task"]
        if endpoint == ENDPOINTS["historical_serps"]:
            body = envelope([snapshot("2026-03-01", 9), snapshot("2026-06-01", 6)])
        elif endpoint == ENDPOINTS["serp"]:
            today = datetime.now(UTC).date().isoformat()
            live = snapshot(today, 4)
            body = {
                "status_code": 20000,
                "cost": 0.002,
                "tasks": [{"status_code": 20000, "cost": 0.002, "result": [live]}],
            }
        elif endpoint == ENDPOINTS["keyword_history"]:
            body = envelope(
                [
                    {
                        "keyword": k,
                        "history": [
                            {
                                "year": 2026,
                                "month": 8,
                                "keyword_info": {
                                    "cpc": 2.5,
                                    "competition": 0.3,
                                    "monthly_searches": [
                                        {"year": 2026, "month": 7, "search_volume": 900},
                                        {"year": 2026, "month": 8, "search_volume": 1000},
                                    ],
                                },
                            }
                        ],
                    }
                    for k in task["keywords"]
                    if k != "nothing here"
                ]
            )
        elif endpoint == ENDPOINTS["keyword_overview"]:
            body = envelope(
                [
                    {
                        "keyword": k,
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


async def test_rankings_backfill_once_then_add_a_live_snapshot(client, email, vendor):
    user_id, site_id = await make_site(client, email)
    caller = Caller(user_id=user_id, site_id=site_id)
    body = TrackKeywordsRequest(keywords=["Espresso  Machine"])
    uk = markets(["GB"], "en")

    async with unit_of_work() as db:
        first = await keyword_tracking_service.track_rankings(
            db, caller, user_id, site_id, "example.com", body, uk
        )
    assert first.backfilled == ["espresso machine"]
    assert first.snapshots == 3
    assert first.rows == 6
    assert first.site_ranked == ["espresso machine"]

    async with unit_of_work() as db:
        second = await keyword_tracking_service.track_rankings(
            db, caller, user_id, site_id, "example.com", body, uk
        )
    assert second.backfilled == []
    assert second.snapshots == 1
    assert sum(q["endpoint"] == ENDPOINTS["historical_serps"] for q in vendor.sent) == 1

    async with unit_of_work() as db:
        ours = (
            await db.scalars(
                select(SeoRankHistory)
                .where(SeoRankHistory.site_id == site_id, SeoRankHistory.is_site.is_(True))
                .order_by(SeoRankHistory.observed_on)
            )
        ).all()
    assert [(r.observed_on, r.rank_group, r.source) for r in ours] == [
        (date(2026, 3, 1), 9, "history"),
        (date(2026, 6, 1), 6, "history"),
        (datetime.now(UTC).date(), 4, "live"),
    ]
    assert all(r.domain == "example.com" for r in ours)
    assert {r.location_code for r in ours} == {2826}

    r = await client.get("/api/v1/site/seo/tracked", params={"locationCode": 2826})
    assert r.status_code == 200, r.text
    overview = r.json()["data"]
    assert overview["locationCode"] == 2826
    assert {"locationCode": 2826, "languageCode": "en", "country": "GB"} in overview["markets"]
    [tracked] = overview["keywords"]
    assert tracked["keyword"] == "espresso machine"
    assert tracked["position"] == 4
    assert tracked["previousPosition"] == 6
    assert tracked["change"] == 2
    assert tracked["url"] == "https://www.example.com/espresso"
    months = overview["months"]
    history = dict(zip(months, tracked["history"], strict=True))
    assert history["2026-06-01"] == 6 and history["2026-03-01"] == 9
    assert overview["stats"] == {"tracked": 1, "topTen": 1, "moved": 1, "notRanking": 0}


async def test_volumes_merge_ads_history_with_clickstream(client, email, vendor):
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


async def test_the_agent_can_query_both_history_tables():
    granted = (await asyncio.to_thread(bootstrap)).granted
    assert {"seo_rank_history", "seo_volume_history", "site_seo"} <= set(granted)
