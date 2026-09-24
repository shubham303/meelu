import pytest

from tests.integration.site_pages.conftest import (
    list_pages,
    save_extraction,
    save_pages,
    urls,
)

FIXTURE = [
    {
        "url": "https://example.com/",
        "status": 200,
        "title": "Home page",
        "metaDescription": "The home of everything",
        "h1": ["Home"],
        "bodyText": "welcome to the shop",
        "format": "html",
        "lang": "en",
        "wordCount": 500,
        "inSitemap": True,
        "contentHash": "h-home",
        "chunkedFromHash": "h-home",
        "lastCrawledAt": "2024-01-10T00:00:00Z",
        "contentChangedAt": "2024-01-10T00:00:00Z",
        "publishedAt": "2023-01-01T00:00:00Z",
        "canonical": "https://example.com/",
        "embedState": "done",
    },
    {
        "url": "https://example.com/blog/grinders",
        "status": 200,
        "title": "Best grinders",
        "metaDescription": "",
        "h1": [],
        "bodyText": "burr grinders compared",
        "format": "html",
        "lang": "en",
        "wordCount": 1200,
        "inSitemap": True,
        "contentHash": "h-grind",
        "shallow": False,
        "lastCrawledAt": "2024-03-01T00:00:00Z",
        "contentChangedAt": "2024-03-01T00:00:00Z",
        "publishedAt": "2024-02-01T00:00:00Z",
        "robotsDirectives": "index, follow",
        "canonical": "https://example.com/blog/grinders",
    },
    {
        "url": "https://example.com/blog/old-kettles",
        "status": 404,
        "title": None,
        "lang": "de",
        "wordCount": 30,
        "inSitemap": False,
        "shallow": True,
        "shallowReason": "thin",
        "lastCrawledAt": "2023-06-01T00:00:00Z",
        "robotsDirectives": "noindex",
        "canonical": "https://example.com/blog/kettles",
        "embedState": "failed",
    },
    {
        "url": "https://example.com/redirected",
        "status": 301,
        "redirectTo": "https://example.com/",
        "blockedByRobots": True,
        "wordCount": 0,
    },
]


PAGE_TYPES = {
    "https://example.com/": "money",
    "https://example.com/blog/grinders": "informational",
    "https://example.com/blog/old-kettles": "informational",
    "https://example.com/redirected": "utility",
}


CHANGED_AT = {
    "https://example.com/": "2024-01-10T00:00:00Z",
    "https://example.com/blog/grinders": "2024-03-01T00:00:00Z",
}


@pytest.fixture
async def corpus(client, site):
    await save_pages(client, FIXTURE)
    for url, page_type in PAGE_TYPES.items():
        r = await client.get("/api/v1/site/pages/by-url", params={"url": url})
        await save_extraction(client, r.json()["data"]["id"], page_type)
    for url, changed in CHANGED_AT.items():
        r = await client.get("/api/v1/site/pages/by-url", params={"url": url})
        page_id = r.json()["data"]["id"]
        r = await client.patch(f"/api/v1/site/pages/{page_id}", json={"contentChangedAt": changed})
        assert r.status_code == 200, r.text
    return site


async def test_list_defaults_sorted_by_url_with_totals(client, corpus):
    body = await list_pages(client)
    assert body["total"] == 4
    assert body["shown"] == 4
    assert body["offset"] == 0
    assert [p["url"] for p in body["pages"]] == [
        "https://example.com/",
        "https://example.com/blog/grinders",
        "https://example.com/blog/old-kettles",
        "https://example.com/redirected",
    ]
    assert body["pages"][0]["stage"] == "indexed"
    assert body["pages"][1]["stage"] == "crawled"
    assert body["pages"][3]["stage"] == "blocked"
    assert "bodyText" not in body["pages"][0]


async def test_filter_page_type_status_and_stage(client, corpus):
    assert await urls(client, pageType="informational") == [
        "https://example.com/blog/grinders",
        "https://example.com/blog/old-kettles",
    ]
    assert await urls(client, pageTypes="money,utility") == [
        "https://example.com/",
        "https://example.com/redirected",
    ]
    assert await urls(client, status="ok") == [
        "https://example.com/",
        "https://example.com/blog/grinders",
    ]
    assert await urls(client, status="gone") == ["https://example.com/blog/old-kettles"]
    assert await urls(client, status="redirect") == ["https://example.com/redirected"]
    assert await urls(client, statusCode="404") == ["https://example.com/blog/old-kettles"]
    assert len(await urls(client, statusCode=["404", "301"])) == 2
    assert await urls(client, stage="blocked") == ["https://example.com/redirected"]
    assert await urls(client, stage="indexed") == ["https://example.com/"]
    assert await urls(client, stage="skipped") == []


async def test_filter_text_and_missing(client, corpus):
    assert await urls(client, urlContains="blog") == [
        "https://example.com/blog/grinders",
        "https://example.com/blog/old-kettles",
    ]
    assert await urls(client, titleContains="grind") == ["https://example.com/blog/grinders"]
    assert await urls(client, metaContains="home of") == ["https://example.com/"]
    assert await urls(client, textContains="burr") == ["https://example.com/blog/grinders"]
    assert await urls(client, title="Home page") == ["https://example.com/"]
    assert await urls(client, missing="metaDescription,h1") == [
        "https://example.com/blog/grinders",
        "https://example.com/blog/old-kettles",
        "https://example.com/redirected",
    ]
    assert await urls(client, missing="bodyText") == [
        "https://example.com/blog/old-kettles",
        "https://example.com/redirected",
    ]


async def test_filter_booleans(client, corpus):
    assert await urls(client, lang="de") == ["https://example.com/blog/old-kettles"]
    assert await urls(client, format="html") == [
        "https://example.com/",
        "https://example.com/blog/grinders",
    ]
    assert await urls(client, embedState="failed") == ["https://example.com/blog/old-kettles"]
    assert await urls(client, inSitemap="true") == [
        "https://example.com/",
        "https://example.com/blog/grinders",
    ]
    assert await urls(client, shallow="true") == ["https://example.com/blog/old-kettles"]
    assert await urls(client, blockedByRobots="true") == ["https://example.com/redirected"]
    assert await urls(client, redirects="true") == ["https://example.com/redirected"]
    assert await urls(client, noindex="true") == ["https://example.com/blog/old-kettles"]
    assert await urls(client, canonicalElsewhere="true") == ["https://example.com/blog/old-kettles"]
    assert await urls(client, orphan="false") == []
    assert len(await urls(client, orphan="true")) == 4
    assert await urls(client, needsAudit="true") == [
        "https://example.com/",
        "https://example.com/blog/grinders",
    ]


async def test_filter_ranges_and_dates(client, corpus):
    assert await urls(client, minWords="500") == [
        "https://example.com/",
        "https://example.com/blog/grinders",
    ]
    assert await urls(client, maxWords="30") == [
        "https://example.com/blog/old-kettles",
        "https://example.com/redirected",
    ]
    assert await urls(client, minWords="100", maxWords="600") == ["https://example.com/"]
    assert await urls(client, crawledAfter="2024-02-01") == ["https://example.com/blog/grinders"]
    assert await urls(client, crawledBefore="2024-01-01") == [
        "https://example.com/blog/old-kettles",
        "https://example.com/redirected",
    ]
    assert await urls(client, changedAfter="2024-02-01") == ["https://example.com/blog/grinders"]
    assert await urls(client, changedBefore="2024-02-01") == ["https://example.com/"]
    assert await urls(client, publishedAfter="2024-01-01") == ["https://example.com/blog/grinders"]
    assert await urls(client, publishedBefore="2024-01-01") == ["https://example.com/"]


async def test_sort_and_limit_clamp(client, corpus):
    assert await urls(client, sort="words") == [
        "https://example.com/redirected",
        "https://example.com/blog/old-kettles",
        "https://example.com/",
        "https://example.com/blog/grinders",
    ]
    assert (await urls(client, sort="words:desc"))[0] == "https://example.com/blog/grinders"
    assert (await urls(client, sort="status:desc"))[0] == "https://example.com/blog/old-kettles"
    assert (await urls(client, sort="crawled"))[0] == "https://example.com/redirected"
    assert (await urls(client, sort="bogus")) == await urls(client)

    body = await list_pages(client, limit="0")
    assert body["shown"] == 1
    assert body["total"] == 4

    body = await list_pages(client, limit="99999")
    assert body["shown"] == 4

    body = await list_pages(client, offset="2")
    assert body["offset"] == 2
    assert body["shown"] == 2
    assert body["total"] == 4

    r = await client.get("/api/v1/site/pages", params={"limit": "abc"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "limit must be a number."}}

    r = await client.get("/api/v1/site/pages", params={"stage": "nope"})
    assert r.status_code == 400
    assert "stage must be one of" in r.json()["error"]["message"]


async def test_views(client, corpus):
    body = await list_pages(client, view="full", urlContains="grinders")
    page = body["pages"][0]
    assert page["bodyText"] == "burr grinders compared"
    assert page["outLinkCount"] == 0

    body = await list_pages(client, view="export", urlContains="grinders")
    page = body["pages"][0]
    assert page["hasText"] is True
    assert page["outLinkCount"] == 0
    assert page["externalLinkCount"] == 0
    assert page["imageCount"] == 0
    assert page["imageBytes"] == 0
    assert page["headingCount"] == 0
    assert "id" not in page

    body = await list_pages(client, view="text", urlContains="grinders")
    page = body["pages"][0]
    assert page["bodyText"] == "burr grinders compared"
    assert page["stage"] in ("crawled", "indexed")
    assert "outLinkCount" not in page
    assert "headings" not in page

    r = await client.get("/api/v1/site/pages", params={"view": "wide"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "view must be one of slim, full, export, text."}}


async def test_ids_and_urls_filters(client, corpus):
    body = await list_pages(client, urls="https://example.com/,https://example.com/redirected")
    assert body["total"] == 2
    ids = [p["id"] for p in body["pages"]]
    body = await list_pages(client, ids=ids[0])
    assert body["total"] == 1
