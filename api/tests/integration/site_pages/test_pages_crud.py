from tests.integration.site_pages.conftest import save_page


async def test_save_page_normalises_url_and_returns_stage(client, site):
    page = await save_page(client, url="https://Example.com/Guide/", title="Guide")
    assert page["url"] == "https://example.com/Guide"
    assert page["title"] == "Guide"
    assert page["stage"] == "pending"
    assert page["siteId"] == site["id"]
    assert "userId" not in page
    assert "seq" not in page

    again = await save_page(client, url="https://example.com/Guide", title="Guide v2")
    assert again["id"] == page["id"]
    assert again["title"] == "Guide v2"


async def test_save_page_requires_url(client, site):
    r = await client.post("/api/v1/site/pages", json={"title": "No url"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "A page needs a `url`."}}


async def test_get_update_delete_page(client, site):
    page = await save_page(client, url="https://example.com/a", status=200)

    r = await client.get(f"/api/v1/site/pages/{page['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == page["id"]

    r = await client.get("/api/v1/site/pages/spg_missing0")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No page spg_missing0 for this website."}}

    r = await client.put(f"/api/v1/site/pages/{page['id']}", json={"title": "A", "wordCount": 120})
    assert r.status_code == 200
    updated = r.json()["data"]
    assert updated["title"] == "A"
    assert updated["wordCount"] == 120

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"kind": "article"})
    assert r.status_code == 200
    assert r.json()["data"]["kind"] == "article"

    r = await client.delete(f"/api/v1/site/pages/{page['id']}")
    assert r.status_code == 200
    assert r.json()["data"] == {"id": page["id"], "url": page["url"], "deleted": True}

    r = await client.get(f"/api/v1/site/pages/{page['id']}")
    assert r.status_code == 404


async def test_content_hash_change_stamps_content_changed_at(client, site):
    page = await save_page(client, url="https://example.com/hash", status=200)
    assert "contentChangedAt" not in page

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"contentHash": "h1"})
    assert r.status_code == 200
    first = r.json()["data"]
    assert first["contentHash"] == "h1"
    assert first["contentChangedAt"].endswith("Z")

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"contentHash": "h1"})
    assert r.json()["data"]["contentChangedAt"] == first["contentChangedAt"]

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"contentHash": "h2"})
    assert r.json()["data"]["contentChangedAt"] != first["contentChangedAt"]


async def test_derived_and_unknown_fields_rejected(client, site):
    page = await save_page(client, url="https://example.com/derived")

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"inlinks": 4})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == (
        "inlinks cannot be written directly — link-graph numbers are rebuilt from "
        "the stored pages, and visited is the crawl's own sweep mark."
    )

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"visited": True})
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith("visited cannot be written directly")

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={"nope": 1})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "nope is not part of a page."}}

    r = await client.patch(f"/api/v1/site/pages/{page['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Nothing to save."}}


async def test_by_url(client, site):
    page = await save_page(client, url="https://example.com/by-url")

    r = await client.get("/api/v1/site/pages/by-url", params={"url": "https://example.com/by-url/"})
    assert r.status_code == 200
    assert r.json()["data"]["id"] == page["id"]

    r = await client.get("/api/v1/site/pages/by-url", params={"url": "https://example.com/gone"})
    assert r.status_code == 404
    assert r.json() == {
        "error": {"message": "No page https://example.com/gone has been crawled for this website."}
    }

    r = await client.get("/api/v1/site/pages/by-url")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Name the page by `id` or by `url`."}}


async def test_bulk_save_pages(client, site):
    r = await client.post("/api/v1/site/pages", json={"pages": []})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Send `pages: [...]` — a crawl batch with no pages writes nothing."}
    }

    r = await client.post(
        "/api/v1/site/pages",
        json={
            "pages": [
                {"url": "https://example.com/one/", "status": 200, "contentHash": "a"},
                {"url": "https://example.com/two", "status": 404, "inlinks": 99, "depth": 7},
                {"url": "", "status": 200},
            ]
        },
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"pages": 2}

    r = await client.get("/api/v1/site/pages/by-url", params={"url": "https://example.com/two"})
    two = r.json()["data"]
    assert two["inlinks"] == 0
    assert "depth" not in two

    r = await client.get("/api/v1/site/pages/by-url", params={"url": "https://example.com/one"})
    one = r.json()["data"]
    assert one["contentHash"] == "a"
    stamped = one["contentChangedAt"]

    r = await client.post(
        "/api/v1/site/pages",
        json={"pages": [{"url": "https://example.com/one", "status": 200, "contentHash": "a"}]},
    )
    assert r.json()["data"] == {"pages": 1}
    r = await client.get("/api/v1/site/pages/by-url", params={"url": "https://example.com/one"})
    assert r.json()["data"]["contentChangedAt"] == stamped

    r = await client.post(
        "/api/v1/site/pages",
        json={"pages": [{"url": "https://example.com/one", "status": 200, "contentHash": "b"}]},
    )
    assert r.json()["data"] == {"pages": 1}
    r = await client.get("/api/v1/site/pages/by-url", params={"url": "https://example.com/one"})
    assert r.json()["data"]["contentChangedAt"] != stamped
