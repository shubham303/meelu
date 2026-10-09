from src.core.database import unit_of_work
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from tests.integration.site_pages.conftest import save_links, save_page, save_pages


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
        known = await site_pages.crawl_known_pages(db, site["id"])
        count = await site_pages.count(db, site["id"])

    assert count == 2
    by_url = {p.url: p.model_dump(mode="json", by_alias=True) for p in known}
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


async def test_outlinks_resolve_to_pages_and_report_the_rest(client, site):
    await save_pages(
        client,
        [
            {"url": "https://example.com/", "status": 200},
            {"url": "https://example.com/known", "status": 200},
        ],
    )
    result = await save_links(
        client,
        [
            {
                "url": "https://example.com/",
                "links": [
                    {"url": "https://example.com/known/", "anchor": "known"},
                    {"url": "https://example.com/new", "anchor": "new"},
                    {"url": "https://example.com", "anchor": "home"},
                ],
            },
            {
                "url": "https://example.com/known",
                "links": [{"url": "https://example.com/", "anchor": "home"}],
            },
        ],
    )

    assert result == {"pages": 2, "links": 2, "unresolved": ["https://example.com/new"]}
    async with unit_of_work() as db:
        home = await site_pages.id_by_url(db, site["id"], "https://example.com/")
        known = await site_pages.id_by_url(db, site["id"], "https://example.com/known")
        edges = await site_page_links.adjacency(db, site["id"])
    assert edges == {home: {known}, known: {home}}


async def test_external_links_live_on_the_page(client, site):
    saved = await save_page(
        client,
        url="https://example.com/",
        status=200,
        externalLinks=[
            {"url": "https://github.com/x", "anchor": "GitHub", "region": "footer"},
            {"url": "https://github.com/x", "region": "footer", "rel": "nofollow"},
            {"url": "https://x.com/y", "rel": "nofollow"},
        ],
    )

    assert saved["externalLinks"] == [
        {
            "url": "https://github.com/x",
            "region": "footer",
            "rel": None,
            "anchor": "GitHub",
            "count": 2,
            "followable": True,
        },
        {
            "url": "https://x.com/y",
            "region": "body",
            "rel": "nofollow",
            "anchor": None,
            "count": 1,
            "followable": False,
        },
    ]
    r = await client.get(f"/api/v1/site/pages/{saved['id']}/links")
    assert [link["url"] for link in r.json()["data"]["external"]] == [
        "https://github.com/x",
        "https://x.com/y",
    ]


async def test_stamp_sitemap_presence(client, site):
    await save_pages(
        client,
        [
            {"url": "https://example.com/a", "status": 200, "inSitemap": True},
            {"url": "https://example.com/b", "status": 200},
        ],
    )

    async with unit_of_work() as db:
        result = await site_pages.stamp_sitemap_presence(
            db, site["id"], ["https://example.com/b", "https://example.com/c"]
        )

    assert result.model_dump() == {"known": 2, "listed": 1}

    r = await client.get("/api/v1/site/pages", params={"inSitemap": "true"})
    assert [p["url"] for p in r.json()["data"]] == ["https://example.com/b"]
