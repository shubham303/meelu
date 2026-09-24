import pytest

from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

ORIGIN = "https://render.example.com"


@pytest.fixture(autouse=True)
def mount_routers():
    from src.app import app
    from src.render_jobs.endpoints import router as render_router
    from src.site_pages.endpoints import router as pages_router

    for router, prefix in (
        (render_router, "/api/v1/site/render-jobs"),
        (pages_router, "/api/v1/site/pages"),
    ):
        mounted = any(str(getattr(r, "path", "")).startswith(prefix) for r in app.routes)
        if not mounted:
            app.include_router(router, prefix="/api/v1")


def page(url, **facts):
    return {"url": f"{ORIGIN}{url}", "in_sitemap": True, "inlinks": 1, **facts}


async def prepare(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post(
        "/api/v1/sites", json={"domain": "render.example.com", "name": "Render Example"}
    )
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    pages = await seed_pages(
        site["id"],
        user_id,
        [
            page("/", page_type="money", depth=0, inlinks=5, title="Home", word_count=30),
            page("/app", page_type="utility", depth=1, title=None, word_count=5),
            page("/docs", page_type="support", depth=1, title="Docs", word_count=800),
            page("/dead", status=404, shallow=True),
            page("/private", blocked_by_robots=True),
        ],
    )
    return site, pages


async def test_render_job_lifecycle(client, email):
    site, pages = await prepare(client, email)

    r = await client.get("/api/v1/site/render-jobs")
    assert r.status_code == 200, r.text
    status = r.json()["data"]["status"]
    assert status["state"] == "idle"
    assert status["device"] == "desktop"
    assert status["renderedPages"] == 0
    assert status["eligiblePages"] == 3
    assert status["pendingPages"] == 3
    assert status["lastRenderedAt"] is None

    r = await client.get("/api/v1/site/render-jobs", params={"device": "tablet"})
    assert r.status_code == 400

    r = await client.post(
        "/api/v1/site/render-jobs",
        json={"trigger": "user", "scope": "all", "userAgentProfile": "generic"},
    )
    assert r.status_code == 202, r.text
    opened = r.json()["data"]
    assert opened["started"] is True
    job = opened["job"]
    assert job["status"] == "queued"
    assert job["scope"] == "all"
    assert job["device"] == "desktop"
    assert job["userAgentProfile"] == "generic"

    r = await client.post("/api/v1/site/render-jobs", json={})
    assert r.status_code == 409

    r = await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")
    assert r.status_code == 200, r.text
    claimed = r.json()["data"]
    assert claimed["job"]["status"] == "running"
    assert claimed["job"]["device"] == "desktop"
    assert claimed["job"]["total"] == 3
    assert claimed["target"]["domain"] == "render.example.com"
    urls = {p["url"] for p in claimed["pages"]}
    assert urls == {f"{ORIGIN}/", f"{ORIGIN}/app", f"{ORIGIN}/docs"}
    assert all(p["renderedFromHash"] is None for p in claimed["pages"])

    r = await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")
    assert r.status_code == 409

    r = await client.patch(
        f"/api/v1/site/render-jobs/{job['id']}", json={"heartbeat": True, "rendered": 1}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"stop": False}

    r = await client.patch(f"/api/v1/site/render-jobs/{job['id']}", json={"status": "cancelling"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "cancelling"

    r = await client.patch(f"/api/v1/site/render-jobs/{job['id']}", json={"heartbeat": True})
    assert r.json()["data"] == {"stop": True}

    r = await client.patch(
        f"/api/v1/site/render-jobs/{job['id']}",
        json={"status": "cancelled", "rendered": 1, "failed": 0},
    )
    assert r.status_code == 200, r.text
    settled = r.json()["data"]
    assert settled["status"] == "cancelled"
    assert settled["rendered"] == 1
    assert settled["finishedAt"] is not None

    r = await client.get("/api/v1/site/render-jobs")
    status = r.json()["data"]["status"]
    assert status["state"] == "cancelled"
    assert status["active"] is False
    assert status["jobId"] == job["id"]

    r = await client.get("/api/v1/site/render-jobs", params={"device": "mobile"})
    assert r.json()["data"]["status"]["state"] == "idle"


async def test_status_and_claim_are_per_device(client, email):
    site, pages = await prepare(client, email)
    app_id = pages[f"{ORIGIN}/app"]
    docs_id = pages[f"{ORIGIN}/docs"]
    for page_id, hash_ in ((app_id, "h-app"), (docs_id, "h-docs")):
        r = await client.post(
            "/api/v1/site/page-renders",
            json={"pageId": page_id, "device": "mobile", "renderedFromHash": hash_, "title": "m"},
        )
        assert r.status_code == 201, r.text
    r = await client.post(
        "/api/v1/site/page-renders",
        json={"pageId": app_id, "device": "mobile", "renderedFromHash": "stale", "title": "m"},
    )
    assert r.json()["data"]["renderedFromHash"] == "stale"

    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage

    async with SessionLocal() as db:
        await db.execute(
            update(SitePage).where(SitePage.id == docs_id).values(content_hash="h-docs")
        )
        await db.execute(update(SitePage).where(SitePage.id == app_id).values(content_hash="h-app"))
        await db.commit()

    r = await client.get("/api/v1/site/render-jobs", params={"device": "mobile"})
    status = r.json()["data"]["status"]
    assert status["device"] == "mobile"
    assert status["renderedPages"] == 2
    assert status["pendingPages"] == 2
    assert status["lastRenderedAt"] is not None

    r = await client.get("/api/v1/site/render-jobs", params={"device": "desktop"})
    status = r.json()["data"]["status"]
    assert status["renderedPages"] == 0
    assert status["pendingPages"] == 3

    r = await client.post("/api/v1/site/render-jobs", json={"scope": "all", "device": "mobile"})
    assert r.status_code == 202, r.text
    job = r.json()["data"]["job"]
    assert job["device"] == "mobile"
    r = await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")
    claimed = r.json()["data"]
    assert claimed["job"]["device"] == "mobile"
    hashes = {p["url"]: p["renderedFromHash"] for p in claimed["pages"]}
    assert hashes[f"{ORIGIN}/docs"] == "h-docs"
    assert hashes[f"{ORIGIN}/app"] == "stale"
    assert hashes[f"{ORIGIN}/"] is None

    r = await client.get("/api/v1/site/render-jobs", params={"device": "mobile"})
    assert r.json()["data"]["status"]["active"] is True
    r = await client.get("/api/v1/site/render-jobs", params={"device": "desktop"})
    assert r.json()["data"]["status"]["active"] is False


async def test_reap_clears_a_job_left_running(client, email):
    site, _ = await prepare(client, email)
    r = await client.post("/api/v1/site/render-jobs", json={})
    job = r.json()["data"]["job"]
    await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")

    r = await client.post("/api/v1/site/render-jobs/reap", json={"staleMs": 0})
    assert r.status_code == 200, r.text
    reaped = r.json()["data"]
    assert reaped["reaped"] == 1
    assert reaped["jobs"][0]["id"] == job["id"]
    assert reaped["jobs"][0]["status"] == "failed"


async def test_sample_scope_limits_pages_per_page_type(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post(
        "/api/v1/sites", json={"domain": "render.example.com", "name": "Render Example"}
    )
    site = r.json()["data"]
    await seed_pages(
        site["id"],
        user_id,
        [page(f"/blog/{n}", page_type="informational", depth=2, inlinks=n) for n in range(15)]
        + [page(f"/p/{n}", page_type="money", depth=1, inlinks=n) for n in range(3)],
    )

    r = await client.post("/api/v1/site/render-jobs", json={"scope": "sample"})
    job = r.json()["data"]["job"]
    r = await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")
    claimed = r.json()["data"]
    counts = {}
    for p in claimed["pages"]:
        counts[p["pageType"]] = counts.get(p["pageType"], 0) + 1
    assert counts == {"informational": 10, "money": 3}
    articles = [p["url"] for p in claimed["pages"] if p["pageType"] == "informational"]
    assert f"{ORIGIN}/blog/14" in articles
    assert f"{ORIGIN}/blog/0" not in articles


async def test_page_render_upsert_read_and_delete(client, email):
    site, pages = await prepare(client, email)
    page_id = pages[f"{ORIGIN}/app"]

    r = await client.get("/api/v1/site/page-renders", params={"pageId": page_id})
    assert r.status_code == 404

    body = {
        "pageId": page_id,
        "renderedFromHash": "abc",
        "finalUrl": f"{ORIGIN}/app",
        "title": "Rendered App",
        "h1": ["Welcome"],
        "wordCount": 640,
        "internalLinks": 42,
        "schemaTypes": ["WebPage"],
        "consoleErrors": 2,
        "consoleSamples": [{"level": "error", "text": "Uncaught TypeError"}],
        "failedRequests": 1,
        "failedSamples": [{"url": f"{ORIGIN}/api/data", "status": 500}],
        "jsBytes": 2_100_000,
        "totalBytes": 3_000_000,
        "requestCount": 88,
        "thirdPartyHosts": ["cdn.example.net"],
        "status": 200,
        "settleReason": "idle",
        "internalLinkUrls": [f"{ORIGIN}/", f"{ORIGIN}/docs"],
        "images": [{"src": f"{ORIGIN}/hero.png", "alt": "Hero"}, {"src": f"{ORIGIN}/b.png"}],
        "hreflang": {"en": f"{ORIGIN}/app", "x-default": f"{ORIGIN}/app"},
        "overlayCoverage": 0.62,
        "serviceWorker": True,
        "htmlPath": "/tmp/render.html",
    }
    r = await client.post("/api/v1/site/page-renders", json=body)
    assert r.status_code == 201, r.text
    saved = r.json()["data"]
    assert saved["pageId"] == page_id
    assert saved["title"] == "Rendered App"
    assert saved["wordCount"] == 640
    assert saved["consoleSamples"] == [{"level": "error", "text": "Uncaught TypeError"}]
    assert saved["renderError"] is None
    assert saved["userAgentProfile"] == "googlebot"
    assert saved["device"] == "desktop"
    assert saved["hiddenWordCount"] is None
    assert saved["status"] == 200
    assert saved["settleReason"] == "idle"
    assert saved["internalLinkUrls"] == [f"{ORIGIN}/", f"{ORIGIN}/docs"]
    assert saved["images"] == [
        {"src": f"{ORIGIN}/hero.png", "alt": "Hero"},
        {"src": f"{ORIGIN}/b.png"},
    ]
    assert saved["hreflang"] == {"en": f"{ORIGIN}/app", "x-default": f"{ORIGIN}/app"}
    assert saved["overlayCoverage"] == pytest.approx(0.62)
    assert saved["serviceWorker"] is True
    assert saved["mixedContentActive"] == 0
    first_id = saved["id"]

    r = await client.post(
        "/api/v1/site/page-renders",
        json={
            "pageId": page_id,
            "device": "mobile",
            "title": "Rendered App on a phone",
            "hiddenWordCount": 240,
            "hiddenInternalLinks": 12,
            "viewportOverflowPx": 48,
            "smallTapTargets": 7,
        },
    )
    assert r.status_code == 201, r.text
    mobile = r.json()["data"]
    assert mobile["id"] != first_id
    assert mobile["device"] == "mobile"
    assert mobile["hiddenWordCount"] == 240
    assert mobile["hiddenInternalLinks"] == 12
    assert mobile["viewportOverflowPx"] == 48
    assert mobile["smallTapTargets"] == 7

    r = await client.get(
        "/api/v1/site/page-renders", params={"pageId": page_id, "device": "mobile"}
    )
    assert r.json()["data"]["title"] == "Rendered App on a phone"
    r = await client.get("/api/v1/site/page-renders", params={"pageId": page_id})
    assert r.json()["data"]["title"] == "Rendered App"

    r = await client.post(
        "/api/v1/site/page-renders",
        json={"pageId": page_id, "renderError": "timed out", "userAgentProfile": "ai_bot"},
    )
    assert r.status_code == 201, r.text
    again = r.json()["data"]
    assert again["id"] == first_id
    assert again["renderError"] == "timed out"
    assert again["wordCount"] == 0
    assert again["title"] is None

    r = await client.get("/api/v1/site/page-renders", params={"pageId": page_id})
    assert r.status_code == 200
    assert r.json()["data"]["renderError"] == "timed out"

    r = await client.post("/api/v1/site/page-renders", json={"pageId": "pg_nope"})
    assert r.status_code == 404

    r = await client.delete("/api/v1/site/page-renders", params={"pageId": page_id})
    assert r.status_code == 204
    r = await client.get("/api/v1/site/page-renders", params={"pageId": page_id})
    assert r.status_code == 404
    r = await client.get(
        "/api/v1/site/page-renders", params={"pageId": page_id, "device": "mobile"}
    )
    assert r.status_code == 200
    r = await client.delete(
        "/api/v1/site/page-renders", params={"pageId": page_id, "device": "mobile"}
    )
    assert r.status_code == 204


async def test_render_job_can_target_one_page_or_cap_the_count(client, email):
    site, pages = await prepare(client, email)

    r = await client.post("/api/v1/site/render-jobs", json={"scope": "all", "limit": 2})
    assert r.status_code == 202, r.text
    job = r.json()["data"]["job"]
    assert job["pageLimit"] == 2
    r = await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]["pages"]) == 2
    await client.patch(f"/api/v1/site/render-jobs/{job['id']}", json={"status": "completed"})

    r = await client.post("/api/v1/site/render-jobs", json={"url": f"{ORIGIN}/docs"})
    assert r.status_code == 202, r.text
    job = r.json()["data"]["job"]
    assert job["pageUrl"] == f"{ORIGIN}/docs"
    r = await client.post(f"/api/v1/site/render-jobs/{job['id']}/claim")
    assert [p["url"] for p in r.json()["data"]["pages"]] == [f"{ORIGIN}/docs"]
    await client.patch(f"/api/v1/site/render-jobs/{job['id']}", json={"status": "completed"})

    r = await client.post("/api/v1/site/render-jobs", json={"url": "not a url", "limit": 0})
    assert r.status_code == 202, r.text
    job = r.json()["data"]["job"]
    assert job["pageUrl"] is None
    assert job["pageLimit"] is None
