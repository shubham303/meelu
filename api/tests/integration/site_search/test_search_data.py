from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import signup


def day_ago(n: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=n)).isoformat()


DAY_A = day_ago(4)
DAY_B = day_ago(3)

BATCH = {
    "days": [
        {
            "day": DAY_A,
            "rows": [
                {
                    "query": "espresso machine",
                    "page": "https://example.com/pricing",
                    "clicks": 10,
                    "impressions": 100,
                    "position": 5,
                },
                {
                    "query": "coffee grinder",
                    "page": "https://example.com/pricing",
                    "clicks": 5,
                    "impressions": 50,
                    "position": 10,
                },
                {
                    "query": "espresso machine",
                    "page": "https://example.com/blog/beans",
                    "clicks": 2,
                    "impressions": 20,
                    "position": 3,
                },
            ],
        },
        {
            "day": DAY_B,
            "rows": [
                {
                    "query": "espresso machine",
                    "page": "https://example.com/pricing",
                    "clicks": 20,
                    "impressions": 200,
                    "position": 4,
                },
                {
                    "query": "coffee grinder",
                    "page": "https://example.com/blog/beans",
                    "clicks": 1,
                    "impressions": 10,
                    "position": 12,
                },
            ],
        },
    ]
}

PRICING = "https://example.com/pricing"
BLOG = "https://example.com/blog/beans"


async def make_site(client, domain="example.com", name="Example"):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def seed_page(site, url, title="Pricing", inlinks=7, status=200):
    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage

    async with unit_of_work() as db:
        db.add(
            SitePage(
                id=uid("page"),
                user_id=site["userId"] if "userId" in site else None,
                site_id=site["id"],
                url=url,
                title=title,
                inlinks=inlinks,
                status=status,
            )
        )


async def test_overview_without_data(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.get("/api/v1/site/search-data")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body == {
        "connected": False,
        "property": None,
        "hasData": False,
        "operatingBlind": True,
        "sync": None,
        "active": None,
    }


async def test_property_sets_gsc_property(client, email):
    await signup(client, email)
    site = await make_site(client)

    r = await client.post("/api/v1/site/search-data/property", json={"property": ""})
    assert r.status_code == 400
    assert "property is required" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/site/search-data/property",
        json={"property": "sc-domain:example.com"},
        headers={"x-meelu-site": site["id"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"property": "sc-domain:example.com"}

    r = await client.get("/api/v1/site")
    assert r.json()["data"]["gscProperty"] == "sc-domain:example.com"

    r = await client.get("/api/v1/site/search-data")
    body = r.json()["data"]
    assert body["connected"] is True
    assert body["property"] == "sc-domain:example.com"


async def test_ingest_rows_and_aggregations(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.post("/api/v1/site/search-data/rows", json=BATCH)
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"days": 2, "rows": 5}

    r = await client.get("/api/v1/site/search-data")
    body = r.json()["data"]
    assert body["hasData"] is True
    assert body["operatingBlind"] is False
    assert body["firstDay"] == DAY_A
    assert body["lastDay"] == DAY_B
    assert body["daysStored"] == 2
    assert body["current"]["clicks"] == 38
    assert body["current"]["impressions"] == 380
    assert body["current"]["ctr"] == pytest.approx(38 / 380)
    assert body["current"]["position"] == pytest.approx(1980 / 380)
    assert body["previous"] == {"clicks": 0, "impressions": 0, "ctr": None, "position": None}
    assert len(body["weeklyClicks"]) == 12
    assert body["weeklyClicks"][-1] == 38

    r = await client.get("/api/v1/site/search-data/queries", params={"days": 90})
    body = r.json()["data"]
    assert body["total"] == 2
    assert body["lastDay"] == DAY_B
    assert body["days"] == 90
    top, second = body["rows"]
    assert top["query"] == "espresso machine"
    assert top["clicks"] == 32
    assert top["impressions"] == 320
    assert top["position"] == pytest.approx(1360 / 320)
    assert top["prevClicks"] == 0
    assert top["prevPosition"] is None
    assert top["page"] == PRICING
    assert second["query"] == "coffee grinder"
    assert second["clicks"] == 6
    assert second["impressions"] == 60
    assert second["position"] == pytest.approx(620 / 60)

    r = await client.get("/api/v1/site/search-data/pages", params={"days": 90})
    body = r.json()["data"]
    assert body["total"] == 2
    first, other = body["rows"]
    assert first["page"] == PRICING
    assert first["clicks"] == 35
    assert first["impressions"] == 350
    assert first["position"] == pytest.approx(1800 / 350)
    assert first["topQuery"] == "espresso machine"
    assert first["prevClicks"] == 0
    assert first["weekly"] == [0, 0, 0, 0, 0, 0, 0, 35]
    assert first["pageId"] is None
    assert other["page"] == BLOG
    assert other["clicks"] == 3
    assert other["position"] == pytest.approx(180 / 30)

    r = await client.get("/api/v1/site/search-data/series", params={"days": 90})
    body = r.json()["data"]
    assert body["hasData"] is True
    assert body["lastDay"] == DAY_B
    assert body["days"] == 90
    assert len(body["series"]) == 1
    points = body["series"][0]["points"]
    assert body["series"][0]["page"] is None
    assert len(points) == 90
    assert points[-1]["day"] == DAY_B
    by_day = {p["day"]: p for p in points}
    assert by_day[DAY_A]["clicks"] == 17
    assert by_day[DAY_A]["impressions"] == 170
    assert by_day[DAY_A]["position"] == pytest.approx(1060 / 170)
    assert by_day[DAY_A]["ctr"] == pytest.approx(17 / 170)
    assert by_day[DAY_B]["clicks"] == 21
    assert by_day[DAY_B]["impressions"] == 210
    assert by_day[DAY_B]["position"] == pytest.approx(920 / 210)
    empty = by_day[day_ago(40)]
    assert empty == {
        "day": day_ago(40),
        "clicks": 0,
        "impressions": 0,
        "ctr": None,
        "position": None,
    }
    assert body["current"]["clicks"] == 38

    r = await client.get("/api/v1/site/search-data/series", params={"days": 90, "pages": PRICING})
    body = r.json()["data"]
    assert len(body["series"]) == 1
    assert body["series"][0]["page"] == PRICING
    scoped = {p["day"]: p for p in body["series"][0]["points"]}
    assert scoped[DAY_A]["clicks"] == 15
    assert scoped[DAY_B]["clicks"] == 20
    assert body["current"]["clicks"] == 35
    assert body["current"]["impressions"] == 350

    r = await client.get("/api/v1/site/search-data/pages", params={"url": PRICING, "days": 90})
    body = r.json()["data"]
    assert body["hasData"] is True
    assert body["page"] == PRICING
    assert [q["query"] for q in body["queries"]] == ["espresso machine", "coffee grinder"]
    assert body["queries"][0]["clicks"] == 30

    r = await client.get("/api/v1/site/search-data/changes", params={"days": 90})
    body = r.json()["data"]
    assert body["hasData"] is True
    assert body["lastDay"] == DAY_B
    assert body["down"] == []
    ups = {(m["kind"], m["key"]): m for m in body["up"]}
    assert ups[("page", PRICING)]["clicks"] == 35
    assert ups[("page", PRICING)]["prevClicks"] == 0
    assert ups[("query", "espresso machine")]["clicks"] == 32


async def test_ingest_rows_is_idempotent(client, email):
    await signup(client, email)
    await make_site(client)

    for _ in range(2):
        r = await client.post("/api/v1/site/search-data/rows", json=BATCH)
        assert r.status_code == 200, r.text
        assert r.json()["data"] == {"days": 2, "rows": 5}

    body = (await client.get("/api/v1/site/search-data")).json()["data"]
    assert body["current"]["clicks"] == 38
    assert body["current"]["impressions"] == 380
    assert body["daysStored"] == 2

    pages = (await client.get("/api/v1/site/search-data/pages", params={"days": 90})).json()["data"]
    assert pages["total"] == 2
    assert pages["rows"][0]["clicks"] == 35

    replaced = {
        "days": [
            {
                "day": DAY_B,
                "rows": [
                    {
                        "query": "espresso machine",
                        "page": PRICING,
                        "clicks": 1,
                        "impressions": 2,
                        "position": 9,
                    }
                ],
            }
        ]
    }
    r = await client.post("/api/v1/site/search-data/rows", json=replaced)
    assert r.json()["data"] == {"days": 1, "rows": 1}

    body = (await client.get("/api/v1/site/search-data")).json()["data"]
    assert body["current"]["clicks"] == 18
    assert body["current"]["impressions"] == 172


async def test_ingest_rows_validation(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.post("/api/v1/site/search-data/rows", json={})
    assert r.status_code == 400
    assert "a sync batch with no days writes nothing" in r.json()["error"]["message"]

    r = await client.post("/api/v1/site/search-data/rows", json={"days": []})
    assert r.status_code == 400

    r = await client.post(
        "/api/v1/site/search-data/rows",
        json={"days": [{"day": d, "rows": []} for d in [day_ago(i) for i in range(32)]]},
    )
    assert r.status_code == 400
    assert "At most 31 days per batch" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/site/search-data/rows", json={"days": [{"day": "12-2026", "rows": []}]}
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"] == '"12-2026" is not a YYYY-MM-DD day.'

    r = await client.post(
        "/api/v1/site/search-data/rows",
        json={"days": [{"day": DAY_A, "rows": [{"page": PRICING, "clicks": 3}]}]},
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"days": 1, "rows": 0}


async def test_series_rejects_too_many_pages(client, email):
    await signup(client, email)
    await make_site(client)
    await client.post("/api/v1/site/search-data/rows", json=BATCH)

    pages = ",".join(f"https://example.com/p{n}" for n in range(6))
    r = await client.get("/api/v1/site/search-data/series", params={"pages": pages})
    assert r.status_code == 400
    assert "At most 5 pages can be compared" in r.json()["error"]["message"]

    r = await client.get("/api/v1/site/search-data/queries", params={"pages": pages})
    assert r.status_code == 400
    assert "At most 5 pages can be filtered" in r.json()["error"]["message"]


async def test_operating_blind_under_threshold(client, email):
    await signup(client, email)
    await make_site(client)

    thin = {
        "days": [
            {
                "day": DAY_B,
                "rows": [
                    {
                        "query": "espresso machine",
                        "page": PRICING,
                        "clicks": 1,
                        "impressions": 12,
                        "position": 30,
                    }
                ],
            }
        ]
    }
    await client.post("/api/v1/site/search-data/rows", json=thin)

    body = (await client.get("/api/v1/site/search-data")).json()["data"]
    assert body["hasData"] is True
    assert body["operatingBlind"] is True


async def test_inspections_round_trip(client, email):
    await signup(client, email)
    site = await make_site(client)
    me = (await client.get("/api/auth/me")).json()["data"]
    site = {**site, "userId": me["id"]}

    await seed_page(site, PRICING, title="Pricing", inlinks=9)
    await seed_page(site, BLOG, title="Beans", inlinks=2)

    r = await client.get("/api/v1/site/search-data/inspections")
    assert r.status_code == 200, r.text
    assert sorted(r.json()["data"]["urls"]) == sorted([PRICING, BLOG])

    r = await client.post("/api/v1/site/search-data/inspections", json={"inspections": []})
    assert r.status_code == 400
    assert "a batch with no rows writes nothing" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/site/search-data/inspections",
        json={
            "inspections": [
                {
                    "url": PRICING,
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                    "googleCanonical": PRICING,
                    "lastCrawlTime": "2026-08-01T10:00:00Z",
                },
                {
                    "url": BLOG,
                    "verdict": "NEUTRAL",
                    "coverageState": "Crawled - currently not indexed",
                    "googleCanonical": PRICING,
                },
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"applied": 2}

    await client.post("/api/v1/site/search-data/rows", json=BATCH)
    body = (await client.get("/api/v1/site/search-data")).json()["data"]
    assert body["indexation"] == {"indexed": 1, "crawled-not-indexed": 1}
    assert body["neverChecked"] == 0
    assert body["googlePrefers"] == [
        {
            "url": BLOG,
            "googleCanonical": PRICING,
            "coverageState": "Crawled - currently not indexed",
        }
    ]
    assert body["contentQualityVerdict"] is None

    r = await client.get("/api/v1/site/search-data/inspections")
    assert r.json()["data"]["urls"] == []

    pages = (await client.get("/api/v1/site/search-data/pages", params={"days": 90})).json()["data"]
    top = pages["rows"][0]
    assert top["page"] == PRICING
    assert top["pageId"] is not None
    assert top["title"] == "Pricing"
    assert top["inlinks"] == 9
    assert top["indexState"] == "indexed"
    assert top["coverageState"] == "Submitted and indexed"
    assert top["indexCheckedAt"] is not None


async def test_sync_job_lifecycle(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.post("/api/v1/site/search-data/sync-jobs", json={"trigger": "user"})
    assert r.status_code == 202, r.text
    opened = r.json()["data"]
    assert opened["started"] is True
    sync = opened["sync"]
    assert sync["status"] == "queued"
    assert sync["trigger"] == "user"
    assert sync["daysTotal"] == 0
    assert sync["rowsStored"] == 0
    assert sync["pagesInspected"] == 0
    assert sync["notes"] == []
    assert sync["error"] is None
    assert sync["finishedAt"] is None
    assert "userId" not in sync
    assert "seq" not in sync
    assert "property" not in sync
    sync_id = sync["id"]

    r = await client.post("/api/v1/site/search-data/sync-jobs", json={})
    assert r.status_code == 409
    blocked = r.json()["data"]
    assert blocked["started"] is False
    assert blocked["sync"]["id"] == sync_id
    assert "already running" in blocked["reason"]

    r = await client.get("/api/v1/site/search-data/sync-jobs")
    listed = r.json()["data"]
    assert listed["latest"]["id"] == sync_id
    assert listed["active"]["id"] == sync_id

    r = await client.get(f"/api/v1/site/search-data/sync-jobs/{sync_id}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == sync_id

    r = await client.get("/api/v1/site/search-data/sync-jobs/ssync_missing")
    assert r.status_code == 404

    r = await client.post(f"/api/v1/site/search-data/sync-jobs/{sync_id}/claim")
    assert r.status_code == 200, r.text
    plan = r.json()["data"]
    assert plan["sync"]["status"] == "running"
    assert plan["sync"]["startedAt"] is not None
    assert plan["property"] is None
    assert plan["domain"] == "example.com"
    assert plan["resumeFrom"] is None
    assert plan["endDay"] == day_ago(3)
    assert plan["daysTotal"] > 400
    assert plan["sync"]["daysTotal"] == plan["daysTotal"]
    assert plan["sync"]["firstDay"] == plan["startDay"]
    assert plan["sync"]["lastDay"] == plan["endDay"]

    r = await client.post(f"/api/v1/site/search-data/sync-jobs/{sync_id}/claim")
    assert r.status_code == 409
    assert "This sync is running" in r.json()["error"]["message"]

    r = await client.patch(
        f"/api/v1/site/search-data/sync-jobs/{sync_id}",
        json={"daysDone": 5, "rowsStored": 120, "property": "sc-domain:example.com"},
    )
    assert r.status_code == 200, r.text
    progressed = r.json()["data"]
    assert progressed["status"] == "running"
    assert progressed["daysDone"] == 5
    assert progressed["rowsStored"] == 120
    assert progressed["property"] == "sc-domain:example.com"
    assert progressed["heartbeatAt"] is not None

    r = await client.patch(
        f"/api/v1/site/search-data/sync-jobs/{sync_id}", json={"status": "bogus"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "status must be completed, failed or cancelled."

    r = await client.patch(
        f"/api/v1/site/search-data/sync-jobs/{sync_id}",
        json={
            "status": "completed",
            "daysDone": 480,
            "rowsStored": 900,
            "pagesInspected": 42,
            "notes": ["index inspection stopped early"],
        },
    )
    assert r.status_code == 200, r.text
    settled = r.json()["data"]
    assert settled["status"] == "completed"
    assert settled["daysDone"] == 480
    assert settled["pagesInspected"] == 42
    assert settled["notes"] == ["index inspection stopped early"]
    assert settled["finishedAt"] is not None

    r = await client.patch("/api/v1/site/search-data/sync-jobs/ssync_missing", json={"daysDone": 1})
    assert r.status_code == 404

    r = await client.get("/api/v1/site/search-data/sync-jobs")
    listed = r.json()["data"]
    assert listed["latest"]["id"] == sync_id
    assert listed["active"] is None

    r = await client.post("/api/v1/site/search-data/sync-jobs", json={})
    assert r.status_code == 202
    assert r.json()["data"]["sync"]["id"] != sync_id


async def test_claim_resumes_from_stored_data(client, email):
    await signup(client, email)
    await make_site(client)
    await client.post("/api/v1/site/search-data/rows", json=BATCH)

    opened = (await client.post("/api/v1/site/search-data/sync-jobs", json={})).json()["data"]
    plan = (
        await client.post(f"/api/v1/site/search-data/sync-jobs/{opened['sync']['id']}/claim")
    ).json()["data"]

    assert plan["resumeFrom"] == day_ago(2)
    assert plan["startDay"] == day_ago(2)
    assert plan["endDay"] == day_ago(3)
    assert plan["daysTotal"] == 0


async def test_stalled_sync_is_reaped(client, email):
    from sqlalchemy import update

    from src.core.database import unit_of_work
    from src.site_search.models.site_search_sync import SiteSearchSync

    await signup(client, email)
    await make_site(client)

    opened = (await client.post("/api/v1/site/search-data/sync-jobs", json={})).json()["data"]
    stale_id = opened["sync"]["id"]

    async with unit_of_work() as db:
        await db.execute(
            update(SiteSearchSync)
            .where(SiteSearchSync.id == stale_id)
            .values(heartbeat_at=datetime.now(UTC) - timedelta(hours=2))
        )

    r = await client.post("/api/v1/site/search-data/sync-jobs", json={})
    assert r.status_code == 202, r.text
    assert r.json()["data"]["sync"]["id"] != stale_id

    r = await client.get(f"/api/v1/site/search-data/sync-jobs/{stale_id}")
    reaped = r.json()["data"]
    assert reaped["status"] == "failed"
    assert reaped["error"] == "the process running it stopped reporting"
    assert reaped["finishedAt"] is not None
