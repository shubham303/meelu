from src.core.database import unit_of_work
from src.site_pages.repository import (
    crawl_counts,
    crawl_known_pages,
    link_frontier,
    stamp_sitemap_presence,
)
from tests.integration.site_pages.conftest import save_pages


async def test_crawl_known_pages_and_counts(client, site):
    await save_pages(
        client,
        [
            {
                "url": "https://example.com/done",
                "status": 200,
                "contentHash": "h",
                "chunkedFromHash": "h",
                "bodyText": "body",
                "etag": "W/1",
                "lastModified": "Mon, 01 Jan 2024 00:00:00 GMT",
                "lastCrawledAt": "2024-01-01T00:00:00Z",
            },
            {"url": "https://example.com/pending"},
        ],
    )

    async with unit_of_work() as db:
        known = await crawl_known_pages(db, site["id"])
        counts = await crawl_counts(db, site["id"])

    assert counts == {"pages": 2}
    by_url = {p["url"]: p for p in known}
    done = by_url["https://example.com/done"]
    assert done["crawlComplete"] is True
    assert done["contentHash"] == "h"
    assert done["etag"] == "W/1"
    assert done["lastModified"] == "Mon, 01 Jan 2024 00:00:00 GMT"
    assert done["lastCrawledAt"] == "2024-01-01T00:00:00.000Z"
    assert done["inlinks"] == 0

    pending = by_url["https://example.com/pending"]
    assert pending["crawlComplete"] is False
    assert "contentHash" not in pending
    assert "lastCrawledAt" not in pending


async def test_link_frontier_lists_unknown_targets(client, site):
    await save_pages(
        client,
        [
            {
                "url": "https://example.com/",
                "status": 200,
                "outLinks": [
                    {"url": "https://example.com/known/", "anchor": "known"},
                    {"url": "https://example.com/new", "anchor": "new"},
                ],
            },
            {"url": "https://example.com/known", "status": 200},
        ],
    )

    async with unit_of_work() as db:
        frontier = await link_frontier(db, site["id"])

    assert frontier == ["https://example.com/new"]


async def test_stamp_sitemap_presence(client, site):
    await save_pages(
        client,
        [
            {"url": "https://example.com/a", "status": 200, "inSitemap": True},
            {"url": "https://example.com/b", "status": 200},
        ],
    )

    async with unit_of_work() as db:
        result = await stamp_sitemap_presence(
            db, site["id"], ["https://example.com/b", "https://example.com/c"]
        )

    assert result == {"known": 2, "listed": 1}

    r = await client.get("/api/v1/site/pages", params={"inSitemap": "true"})
    assert [p["url"] for p in r.json()["data"]["pages"]] == ["https://example.com/b"]
