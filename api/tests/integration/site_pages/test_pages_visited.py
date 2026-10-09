from tests.integration.site_pages.conftest import list_pages, save_pages


async def insert_raw_page(client, site_id, url):
    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage
    from src.sites.models.site import Site

    async with unit_of_work() as db:
        site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one()
        page = SitePage(id=uid("spg"), user_id=site.user_id, site_id=site_id, url=url)
        db.add(page)
    return page.id


async def test_sweep_marks_and_prunes(client, site):
    await save_pages(
        client,
        [
            {"url": "https://example.com/keep", "status": 200},
            {"url": "https://example.com/also-keep", "status": 200},
            {"url": "https://example.com/stale", "status": 200},
        ],
    )

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.status_code == 200
    assert r.json()["data"] == {"deleted": 0}

    r = await client.post("/api/v1/site/pages/visited", json={"reset": True})
    assert r.status_code == 200
    assert r.json()["data"] == {"reset": 3}

    r = await client.post(
        "/api/v1/site/pages/visited",
        json={
            "urls": [
                "https://example.com/keep",
                "https://example.com/keep",
                "https://example.com/also-keep",
                "",
            ]
        },
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"visited": 2}

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.json()["data"] == {"deleted": 1}

    body = await list_pages(client)
    assert [p["url"] for p in body["data"]] == [
        "https://example.com/also-keep",
        "https://example.com/keep",
    ]

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.json()["data"] == {"deleted": 0}


async def test_mark_visited_ignores_trailing_slash(client, site):
    page_id = await insert_raw_page(client, site["id"], "https://example.com/legacy/")

    r = await client.post("/api/v1/site/pages/visited", json={"reset": True})
    assert r.json()["data"] == {"reset": 1}

    r = await client.post(
        "/api/v1/site/pages/visited", json={"urls": ["https://example.com/legacy"]}
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"visited": 1}

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.json()["data"] == {"deleted": 0}

    r = await client.get(f"/api/v1/site/pages/{page_id}")
    assert r.status_code == 200


async def test_mark_visited_validation(client, site):
    r = await client.post("/api/v1/site/pages/visited", json={})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Send `urls: [...]` — the pages the crawl just reached."}
    }

    r = await client.post("/api/v1/site/pages/visited", json={"urls": []})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Send `urls: [...]` — the pages the crawl just reached."}
    }

    r = await client.post("/api/v1/site/pages/visited", json={"urls": [1, None]})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "urls.0: Input should be a valid string"}}


async def test_crawl_upsert_marks_visited(client, site):
    await save_pages(client, [{"url": "https://example.com/fresh", "status": 200}])

    r = await client.post("/api/v1/site/pages/visited", json={"reset": True})
    assert r.json()["data"] == {"reset": 1}

    await save_pages(client, [{"url": "https://example.com/fresh", "status": 200}])

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.json()["data"] == {"deleted": 0}
