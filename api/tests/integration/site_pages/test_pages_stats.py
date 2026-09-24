from tests.integration.site_pages.conftest import save_page, save_pages

STATS_FIXTURE = [
    {
        "url": "https://example.com/",
        "status": 200,
        "inSitemap": True,
        "contentHash": "a",
        "chunkedFromHash": "a",
        "bodyText": "home",
    },
    {"url": "https://example.com/thin", "status": 200, "shallow": True, "shallowReason": "thin"},
    {"url": "https://example.com/missing", "status": 404, "inSitemap": True},
    {"url": "https://example.com/boom", "status": 500},
    {"url": "https://example.com/dead", "status": 0},
    {"url": "https://example.com/robots", "blockedByRobots": True, "inSitemap": True},
    {"url": "https://example.com/pending"},
]


async def add_chunk(site_id, page_id, **kwargs):
    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_chunk import SiteChunk
    from src.site_pages.models.site_page import SitePage

    async with unit_of_work() as db:
        page = (await db.execute(select(SitePage).where(SitePage.id == page_id))).scalar_one()
        chunk = SiteChunk(
            id=uid("chk"),
            user_id=page.user_id,
            site_id=site_id,
            page_id=page_id,
            ordinal=kwargs.pop("ordinal", 0),
            text=kwargs.pop("text", "a passage"),
            **kwargs,
        )
        db.add(chunk)
    return chunk


async def test_stats_shape(client, site):
    await save_pages(client, STATS_FIXTURE)

    r = await client.get("/api/v1/site/pages/stats")
    assert r.status_code == 200
    body = r.json()["data"]

    assert body["pages"] == 6
    assert body["blockedByRobots"] == 1
    assert body["blockedAndDiscoverable"] == 1
    assert body["ok"] == 2
    assert body["errored"] == 2
    assert body["gone"] == 1
    assert body["notFound"] == 1
    assert body["serverError"] == 1
    assert body["unreachable"] == 1
    assert body["blocked"] == 0
    assert body["shallow"] == 1
    assert body["notInSitemap"] == 1
    assert body["sitemapMissing"] == 1
    assert body["orphans"] == 1
    assert body["embedFailed"] == 0
    assert body["crawlComplete"] == 3
    assert body["chunks"] == {"total": 0, "embedded": 0, "failed": 0}
    assert body["lastCrawledAt"] is None
    assert body["sitemapUrlCount"] is None

    by_stage = {row["stage"]: row["n"] for row in body["byStage"]}
    assert by_stage == {"indexed": 1, "skipped": 1, "failed": 3, "blocked": 1, "pending": 1}
    by_page_type = {row["pageType"]: row["n"] for row in body["byPageType"]}
    assert by_page_type == {None: 7}
    assert body["byShallowReason"] == [{"reason": "thin", "n": 1}]


async def test_stats_carries_site_fields(client, site):
    r = await client.patch(
        "/api/v1/site",
        json={"sitemapUrls": ["https://example.com/sitemap.xml"]},
    )
    assert r.status_code == 200

    r = await client.get("/api/v1/site/pages/stats")
    assert r.json()["data"]["sitemapUrlCount"] is None


async def test_chunks_route(client, site):
    page = await save_page(client, url="https://example.com/chunked", status=200)

    r = await client.get("/api/v1/site/chunks")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "pageId is required."}}

    r = await client.get("/api/v1/site/chunks", params={"pageId": "spg_nope00000"})
    assert r.status_code == 404

    r = await client.get("/api/v1/site/chunks", params={"pageId": page["id"]})
    assert r.status_code == 200
    assert r.json()["data"] == []

    await add_chunk(site["id"], page["id"], ordinal=1, text="second", heading_path="H")
    await add_chunk(site["id"], page["id"], ordinal=0, text="first", embed_error="boom")

    r = await client.get("/api/v1/site/chunks", params={"pageId": page["id"]})
    chunks = r.json()["data"]
    assert [c["ordinal"] for c in chunks] == [0, 1]
    assert [c["text"] for c in chunks] == ["first", "second"]
    assert chunks[1]["headingPath"] == "H"
    assert chunks[0]["embedError"] == "boom"
    assert chunks[0]["pageId"] == page["id"]
    assert "embedding" not in chunks[0]

    r = await client.get("/api/v1/site/pages/stats")
    assert r.json()["data"]["chunks"] == {"total": 2, "embedded": 0, "failed": 1}
