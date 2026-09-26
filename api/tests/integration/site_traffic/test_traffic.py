from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import signup


def day_ago(n: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=n)).isoformat()


DAY_A = day_ago(3)
DAY_B = day_ago(2)

TOTALS = [
    {
        "day": DAY_A,
        "users": 100,
        "newUsers": 40,
        "sessions": 120,
        "engagedSessions": 80,
        "pageViews": 300,
        "engagementSeconds": 1500.5,
        "keyEvents": 5,
        "revenue": 99.5,
    },
    {
        "day": DAY_B,
        "users": 150,
        "newUsers": 60,
        "sessions": 180,
        "engagedSessions": 120,
        "pageViews": 450,
        "engagementSeconds": 2000.25,
        "keyEvents": 7,
        "revenue": 100.5,
    },
]

CHANNELS = [
    {
        "day": DAY_A,
        "channel": "Organic Search",
        "source": "google",
        "medium": "organic",
        "sessions": 70,
        "users": 60,
        "newUsers": 20,
        "engagedSessions": 50,
        "keyEvents": 3,
        "revenue": 50.5,
    },
    {
        "day": DAY_A,
        "channel": "Direct",
        "source": "(direct)",
        "medium": "(none)",
        "sessions": 50,
        "users": 40,
        "newUsers": 20,
        "engagedSessions": 30,
        "keyEvents": 2,
        "revenue": 49.0,
    },
    {
        "day": DAY_B,
        "channel": "Organic Search",
        "source": "google",
        "medium": "organic",
        "sessions": 100,
        "users": 90,
        "newUsers": 30,
        "engagedSessions": 70,
        "keyEvents": 4,
        "revenue": 60.5,
    },
    {
        "day": DAY_B,
        "channel": "Direct",
        "source": "(direct)",
        "medium": "(none)",
        "sessions": 80,
        "users": 60,
        "newUsers": 30,
        "engagedSessions": 50,
        "keyEvents": 3,
        "revenue": 40.0,
    },
]

LANDING = [
    {
        "day": DAY_A,
        "landingPage": "/pricing",
        "channel": "Organic Search",
        "sessions": 40,
        "engagedSessions": 30,
        "keyEvents": 2,
        "revenue": 20.0,
    },
    {
        "day": DAY_B,
        "landingPage": "/pricing",
        "channel": "Organic Search",
        "sessions": 60,
        "engagedSessions": 40,
        "keyEvents": 3,
        "revenue": 30.0,
    },
    {
        "day": DAY_B,
        "landingPage": "/blog/beans",
        "channel": "Direct",
        "sessions": 25,
        "engagedSessions": 10,
        "keyEvents": 1,
        "revenue": 5.0,
    },
]

PAGES = [
    {
        "day": DAY_A,
        "pagePath": "/pricing",
        "views": 200,
        "users": 80,
        "engagementSeconds": 900.5,
        "keyEvents": 2,
    },
    {
        "day": DAY_B,
        "pagePath": "/pricing",
        "views": 300,
        "users": 100,
        "engagementSeconds": 1100.5,
        "keyEvents": 3,
    },
    {
        "day": DAY_B,
        "pagePath": "/blog/beans",
        "views": 50,
        "users": 20,
        "engagementSeconds": 100.0,
        "keyEvents": 0,
    },
]

EVENTS = [
    {"day": DAY_A, "eventName": "purchase", "eventCount": 12, "users": 9, "keyEvents": 4},
    {"day": DAY_B, "eventName": "purchase", "eventCount": 20, "users": 15, "keyEvents": 6},
    {"day": DAY_B, "eventName": "sign_up", "eventCount": 5, "users": 5, "keyEvents": 5},
]

GEO = [
    {
        "day": DAY_B,
        "country": "India",
        "sessions": 90,
        "users": 70,
        "newUsers": 30,
        "keyEvents": 3,
        "revenue": 42.0,
    },
    {
        "day": DAY_B,
        "country": "United States",
        "sessions": 60,
        "users": 50,
        "newUsers": 20,
        "keyEvents": 2,
        "revenue": 58.0,
    },
]

TECH = [
    {
        "day": DAY_B,
        "deviceCategory": "mobile",
        "os": "iOS",
        "browser": "Safari",
        "sessions": 110,
        "users": 95,
    },
    {
        "day": DAY_B,
        "deviceCategory": "desktop",
        "os": "macOS",
        "browser": "Chrome",
        "sessions": 70,
        "users": 55,
    },
]


async def make_site(client, domain="example.com", name="Example"):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def post_rows(client, report, rows, **kwargs):
    r = await client.post(
        "/api/v1/site/traffic/rows", json={"report": report, "rows": rows}, **kwargs
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def seed_all(client):
    await post_rows(client, "totals", TOTALS)
    await post_rows(client, "channels", CHANNELS)
    await post_rows(client, "landing", LANDING)
    await post_rows(client, "pages", PAGES)
    await post_rows(client, "events", EVENTS)
    await post_rows(client, "geo", GEO)
    await post_rows(client, "tech", TECH)


async def test_overview_without_data(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.get("/api/v1/site/traffic")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    empty_totals = {
        "users": 0,
        "newUsers": 0,
        "sessions": 0,
        "engagedSessions": 0,
        "pageViews": 0,
        "engagementSeconds": 0,
        "keyEvents": 0,
        "revenue": 0,
    }
    assert body == {
        "connected": False,
        "hasData": False,
        "days": 28,
        "daysStored": 0,
        "totals": {"current": empty_totals, "previous": empty_totals},
        "organic": {
            "current": {"sessions": 0, "engagedSessions": 0, "keyEvents": 0, "revenue": 0},
            "previous": {"sessions": 0, "engagedSessions": 0, "keyEvents": 0, "revenue": 0},
        },
        "channels": [],
    }

    for path in (
        "/api/v1/site/traffic/series",
        "/api/v1/site/traffic/breakdown",
        "/api/v1/site/traffic/pages",
        "/api/v1/site/traffic/content",
    ):
        r = await client.get(path)
        assert r.status_code == 200, r.text
        assert r.json()["data"].get("lastDay") is None


async def test_property_get_and_put(client, email):
    await signup(client, email)
    site = await make_site(client)

    r = await client.get("/api/v1/site/traffic/property")
    assert r.status_code == 200
    assert r.json()["data"] == {"domain": "example.com"}

    r = await client.put("/api/v1/site/traffic/property", json={"property": "   "})
    assert r.status_code == 400
    assert "property is required" in r.json()["error"]["message"]

    r = await client.put(
        "/api/v1/site/traffic/property",
        json={"property": "properties/12345"},
        headers={"x-meelu-site": site["id"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"property": "properties/12345"}

    r = await client.get("/api/v1/site/traffic/property")
    assert r.json()["data"] == {"property": "properties/12345", "domain": "example.com"}

    body = (await client.get("/api/v1/site/traffic")).json()["data"]
    assert body["connected"] is True
    assert body["property"] == "properties/12345"

    assert (await client.get("/api/v1/site")).json()["data"]["gaProperty"] == "properties/12345"


async def test_ingest_and_aggregations(client, email):
    await signup(client, email)
    site = await make_site(client)
    me = (await client.get("/api/auth/me")).json()["data"]

    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage

    async with unit_of_work() as db:
        db.add(
            SitePage(
                id=uid("page"),
                user_id=me["id"],
                site_id=site["id"],
                url="https://example.com/pricing",
                title="Pricing",
                status=200,
            )
        )

    assert await post_rows(client, "totals", TOTALS) == {"stored": 2}
    assert await post_rows(client, "channels", CHANNELS) == {"stored": 4}
    assert await post_rows(client, "landing", LANDING) == {"stored": 3}
    assert await post_rows(client, "pages", PAGES) == {"stored": 3}
    assert await post_rows(client, "events", EVENTS) == {"stored": 3}
    assert await post_rows(client, "geo", GEO) == {"stored": 2}
    assert await post_rows(client, "tech", TECH) == {"stored": 2}

    body = (await client.get("/api/v1/site/traffic")).json()["data"]
    assert body["hasData"] is True
    assert body["days"] == 28
    assert body["firstDay"] == DAY_A
    assert body["lastDay"] == DAY_B
    assert body["daysStored"] == 2
    assert body["totals"]["current"] == {
        "users": 250,
        "newUsers": 100,
        "sessions": 300,
        "engagedSessions": 200,
        "pageViews": 750,
        "engagementSeconds": pytest.approx(3500.75),
        "keyEvents": pytest.approx(12.0),
        "revenue": pytest.approx(200.0),
    }
    assert body["totals"]["previous"]["sessions"] == 0
    assert body["organic"]["current"] == {
        "sessions": 170,
        "engagedSessions": 120,
        "keyEvents": pytest.approx(7.0),
        "revenue": pytest.approx(111.0),
    }
    assert body["organic"]["previous"]["sessions"] == 0
    assert [c["key"] for c in body["channels"]] == [["Organic Search"], ["Direct"]]
    assert body["channels"][0]["sessions"] == 170
    assert body["channels"][0]["users"] == 150
    assert body["channels"][0]["engagedSessions"] == 120
    assert body["channels"][0]["prevSessions"] == 0
    assert body["channels"][1]["sessions"] == 130

    body = (await client.get("/api/v1/site/traffic/series", params={"days": 28})).json()["data"]
    assert body["lastDay"] == DAY_B
    assert body["days"] == 28
    assert len(body["points"]) == 2
    first, second = body["points"]
    assert first["day"] == DAY_A
    assert first["sessions"] == 120
    assert first["users"] == 100
    assert first["pageViews"] == 300
    assert first["organicSessions"] == 70
    assert second["day"] == DAY_B
    assert second["sessions"] == 180
    assert second["organicSessions"] == 100
    assert second["revenue"] == pytest.approx(100.5)

    body = (await client.get("/api/v1/site/traffic/breakdown", params={"by": "source"})).json()[
        "data"
    ]
    assert body["by"] == "source"
    assert body["total"] == 2
    assert body["rows"][0]["key"] == ["google", "organic"]
    assert body["rows"][0]["sessions"] == 170
    assert body["rows"][1]["key"] == ["(direct)", "(none)"]

    body = (await client.get("/api/v1/site/traffic/breakdown", params={"by": "event"})).json()[
        "data"
    ]
    assert [r["key"] for r in body["rows"]] == [["purchase"], ["sign_up"]]
    assert body["rows"][0]["sessions"] == 32
    assert body["rows"][0]["users"] == 24
    assert body["rows"][0]["keyEvents"] == pytest.approx(10.0)
    assert body["rows"][0]["engagedSessions"] == 0
    assert body["rows"][0]["revenue"] == pytest.approx(0.0)

    body = (await client.get("/api/v1/site/traffic/breakdown", params={"by": "country"})).json()[
        "data"
    ]
    assert body["rows"][0]["key"] == ["India"]
    assert body["rows"][0]["sessions"] == 90
    assert body["rows"][0]["revenue"] == pytest.approx(42.0)

    body = (await client.get("/api/v1/site/traffic/breakdown", params={"by": "device"})).json()[
        "data"
    ]
    assert [r["key"] for r in body["rows"]] == [["mobile"], ["desktop"]]
    body = (await client.get("/api/v1/site/traffic/breakdown", params={"by": "browser"})).json()[
        "data"
    ]
    assert [r["key"] for r in body["rows"]] == [["Safari"], ["Chrome"]]

    body = (await client.get("/api/v1/site/traffic/breakdown", params={"by": "nonsense"})).json()[
        "data"
    ]
    assert body["by"] == "channel"

    body = (
        await client.get(
            "/api/v1/site/traffic/breakdown", params={"by": "channel", "search": "organ"}
        )
    ).json()["data"]
    assert [r["key"] for r in body["rows"]] == [["Organic Search"]]

    body = (await client.get("/api/v1/site/traffic/pages")).json()["data"]
    assert body["lastDay"] == DAY_B
    assert body["total"] == 2
    top, other = body["pages"]
    assert top["landingPage"] == "/pricing"
    assert top["sessions"] == 100
    assert top["engagedSessions"] == 70
    assert top["keyEvents"] == pytest.approx(5.0)
    assert top["revenue"] == pytest.approx(50.0)
    assert top["prevSessions"] == 0
    assert top["pageId"] is not None
    assert top["url"] == "https://example.com/pricing"
    assert top["title"] == "Pricing"
    assert other["landingPage"] == "/blog/beans"
    assert other.get("pageId") is None

    body = (await client.get("/api/v1/site/traffic/pages", params={"channel": "Direct"})).json()[
        "data"
    ]
    assert [p["landingPage"] for p in body["pages"]] == ["/blog/beans"]

    body = (await client.get("/api/v1/site/traffic/pages", params={"search": "blog"})).json()[
        "data"
    ]
    assert [p["landingPage"] for p in body["pages"]] == ["/blog/beans"]

    body = (await client.get("/api/v1/site/traffic/pages", params={"sort": "revenue"})).json()[
        "data"
    ]
    assert body["pages"][0]["landingPage"] == "/pricing"

    r = await client.get("/api/v1/site/traffic/pages", params={"sort": "bogus"})
    assert r.status_code == 400
    assert (
        r.json()["error"]["message"] == "sort must be one of sessions, keyEvents, revenue, delta."
    )

    body = (await client.get("/api/v1/site/traffic/content")).json()["data"]
    assert body["total"] == 2
    top, other = body["pages"]
    assert top["pagePath"] == "/pricing"
    assert top["views"] == 500
    assert top["users"] == 180
    assert top["engagementSeconds"] == pytest.approx(2001.0)
    assert top["keyEvents"] == pytest.approx(5.0)
    assert top["prevViews"] == 0
    assert other["pagePath"] == "/blog/beans"
    assert other["views"] == 50

    body = (await client.get("/api/v1/site/traffic/content", params={"sort": "users"})).json()[
        "data"
    ]
    assert body["pages"][0]["pagePath"] == "/pricing"

    r = await client.get("/api/v1/site/traffic/content", params={"sort": "revenue"})
    assert r.status_code == 400

    body = (await client.get("/api/v1/site/traffic/rows", params={"report": "totals"})).json()[
        "data"
    ]
    assert body["report"] == "totals"
    assert body["total"] == 2
    assert [r["day"] for r in body["rows"]] == [DAY_A, DAY_B]
    assert body["rows"][0]["users"] == 100
    assert body["rows"][0]["engagementSeconds"] == pytest.approx(1500.5)

    body = (
        await client.get(
            "/api/v1/site/traffic/rows", params={"report": "channels", "limit": 2, "offset": 1}
        )
    ).json()["data"]
    assert body["total"] == 4
    assert len(body["rows"]) == 2
    assert set(body["rows"][0]) == {
        "day",
        "channel",
        "source",
        "medium",
        "sessions",
        "users",
        "newUsers",
        "engagedSessions",
        "keyEvents",
        "revenue",
    }


async def test_ingest_is_idempotent(client, email):
    await signup(client, email)
    await make_site(client)

    for _ in range(2):
        await seed_all(client)

    body = (await client.get("/api/v1/site/traffic")).json()["data"]
    assert body["totals"]["current"]["sessions"] == 300
    assert body["totals"]["current"]["users"] == 250
    assert body["daysStored"] == 2
    assert body["organic"]["current"]["sessions"] == 170
    assert [c["sessions"] for c in body["channels"]] == [170, 130]

    rows = (await client.get("/api/v1/site/traffic/rows", params={"report": "totals"})).json()[
        "data"
    ]
    assert rows["total"] == 2
    rows = (await client.get("/api/v1/site/traffic/rows", params={"report": "channels"})).json()[
        "data"
    ]
    assert rows["total"] == 4
    rows = (await client.get("/api/v1/site/traffic/rows", params={"report": "landing"})).json()[
        "data"
    ]
    assert rows["total"] == 3

    revised = [{**TOTALS[1], "sessions": 500, "users": 400}]
    assert await post_rows(client, "totals", revised) == {"stored": 1}

    body = (await client.get("/api/v1/site/traffic")).json()["data"]
    assert body["totals"]["current"]["sessions"] == 620
    assert body["totals"]["current"]["users"] == 500
    rows = (await client.get("/api/v1/site/traffic/rows", params={"report": "totals"})).json()[
        "data"
    ]
    assert rows["total"] == 2


async def test_ingest_validation(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.post("/api/v1/site/traffic/rows", json={"rows": TOTALS})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "Missing required field(s): report"

    r = await client.post("/api/v1/site/traffic/rows", json={"report": "sessions", "rows": TOTALS})
    assert r.status_code == 400

    r = await client.post("/api/v1/site/traffic/rows", json={"report": "totals", "rows": []})
    assert r.status_code == 400
    assert "a batch with no rows writes nothing" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/site/traffic/rows",
        json={"report": "totals", "rows": [{"day": "2026/09/01", "sessions": 1}]},
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"] == '"2026/09/01" is not a YYYY-MM-DD day.'

    r = await client.post(
        "/api/v1/site/traffic/rows",
        json={
            "report": "channels",
            "rows": [
                {
                    "day": DAY_B,
                    "channel": "",
                    "source": "google",
                    "medium": "organic",
                    "sessions": 5,
                },
                {
                    "day": DAY_B,
                    "channel": "Direct",
                    "source": "(direct)",
                    "medium": "(none)",
                    "sessions": 5,
                },
            ],
        },
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"stored": 1}

    r = await client.post(
        "/api/v1/site/traffic/rows",
        json={"report": "totals", "rows": [{"day": DAY_B, "sessions": -20, "users": "12"}]},
    )
    assert r.status_code == 200
    rows = (await client.get("/api/v1/site/traffic/rows", params={"report": "totals"})).json()[
        "data"
    ]
    assert rows["rows"][0]["sessions"] == 0
    assert rows["rows"][0]["users"] == 12

    r = await client.get("/api/v1/site/traffic/rows", params={"report": "unknown"})
    assert r.status_code == 400


async def test_sync_job_lifecycle(client, email):
    await signup(client, email)
    await make_site(client)

    r = await client.post("/api/v1/site/traffic/sync-jobs", json={"trigger": "schedule"})
    assert r.status_code == 202, r.text
    opened = r.json()["data"]
    assert opened["started"] is True
    sync = opened["sync"]
    assert sync["status"] == "queued"
    assert sync["trigger"] == "schedule"
    assert sync["notes"] == []
    assert sync.get("error") is None
    assert sync.get("finishedAt") is None
    assert "pagesInspected" not in sync
    assert "userId" not in sync
    sync_id = sync["id"]

    r = await client.post("/api/v1/site/traffic/sync-jobs", json={})
    assert r.status_code == 409
    blocked = r.json()
    assert blocked["started"] is False
    assert blocked["sync"]["id"] == sync_id
    assert "A traffic sync for example.com is already running." == blocked["reason"]

    r = await client.get("/api/v1/site/traffic/sync-jobs")
    listed = r.json()["data"]
    assert listed["latest"]["id"] == sync_id
    assert listed["active"]["id"] == sync_id

    r = await client.get("/api/v1/site/traffic/sync-jobs/tsync_missing")
    assert r.status_code == 404
    assert r.json()["error"]["message"] == "No such traffic sync for this website."

    r = await client.post(f"/api/v1/site/traffic/sync-jobs/{sync_id}/claim")
    assert r.status_code == 200, r.text
    plan = r.json()["data"]
    assert plan["sync"]["status"] == "running"
    assert plan.get("property") is None
    assert plan["domain"] == "example.com"
    assert plan.get("resumeFrom") is None
    assert plan["endDay"] == day_ago(2)
    assert plan["daysTotal"] > 400
    assert plan["sync"]["firstDay"] == plan["startDay"]

    r = await client.post(f"/api/v1/site/traffic/sync-jobs/{sync_id}/claim")
    assert r.status_code == 409

    r = await client.patch(
        f"/api/v1/site/traffic/sync-jobs/{sync_id}",
        json={"daysDone": 28, "rowsStored": 400, "property": "properties/999"},
    )
    assert r.status_code == 200, r.text
    progressed = r.json()["data"]
    assert progressed["daysDone"] == 28
    assert progressed["rowsStored"] == 400
    assert progressed["property"] == "properties/999"
    assert progressed["heartbeatAt"] is not None
    assert progressed["status"] == "running"

    r = await client.patch(f"/api/v1/site/traffic/sync-jobs/{sync_id}", json={"status": "done"})
    assert r.status_code == 400

    r = await client.patch(
        f"/api/v1/site/traffic/sync-jobs/{sync_id}",
        json={"status": "cancelled", "daysDone": 30, "rowsStored": 500, "error": "stopped by user"},
    )
    assert r.status_code == 200
    settled = r.json()["data"]
    assert settled["status"] == "cancelled"
    assert settled["error"] == "stopped by user"
    assert settled["finishedAt"] is not None

    r = await client.get("/api/v1/site/traffic/sync-jobs")
    listed = r.json()["data"]
    assert listed["latest"]["id"] == sync_id
    assert listed.get("active") is None

    r = await client.patch("/api/v1/site/traffic/sync-jobs/tsync_missing", json={"daysDone": 1})
    assert r.status_code == 404


async def test_claim_resumes_from_stored_data(client, email):
    await signup(client, email)
    await make_site(client)
    await post_rows(client, "totals", TOTALS)

    opened = (await client.post("/api/v1/site/traffic/sync-jobs", json={})).json()["data"]
    plan = (
        await client.post(f"/api/v1/site/traffic/sync-jobs/{opened['sync']['id']}/claim")
    ).json()["data"]

    assert plan["resumeFrom"] == day_ago(1)
    assert plan["startDay"] == day_ago(1)
    assert plan["endDay"] == day_ago(2)
    assert plan["daysTotal"] == 0


async def test_stalled_sync_is_reaped(client, email):
    from sqlalchemy import update

    from src.core.database import unit_of_work
    from src.site_traffic.models.site_traffic_sync import SiteTrafficSync

    await signup(client, email)
    await make_site(client)

    opened = (await client.post("/api/v1/site/traffic/sync-jobs", json={})).json()["data"]
    stale_id = opened["sync"]["id"]

    async with unit_of_work() as db:
        await db.execute(
            update(SiteTrafficSync)
            .where(SiteTrafficSync.id == stale_id)
            .values(heartbeat_at=datetime.now(UTC) - timedelta(hours=2))
        )

    r = await client.post("/api/v1/site/traffic/sync-jobs", json={})
    assert r.status_code == 202, r.text
    assert r.json()["data"]["sync"]["id"] != stale_id

    reaped = (await client.get(f"/api/v1/site/traffic/sync-jobs/{stale_id}")).json()["data"]
    assert reaped["status"] == "failed"
    assert reaped["error"] == "the process running it stopped reporting"
    assert reaped["finishedAt"] is not None
