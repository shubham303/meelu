from tests.integration.site_pages.conftest import list_pages, save_pages


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

    r = await client.post("/api/v1/site/pages/sweep")
    assert r.status_code == 200
    assert r.json()["data"] == {"reset": 3}

    await save_pages(
        client,
        [
            {"url": "https://example.com/keep", "status": 200},
            {"url": "https://example.com/also-keep", "status": 200},
        ],
    )

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.json()["data"] == {"deleted": 1}

    body = await list_pages(client)
    assert [p["url"] for p in body["data"]] == [
        "https://example.com/also-keep",
        "https://example.com/keep",
    ]

    r = await client.post("/api/v1/site/pages/prune", json={})
    assert r.json()["data"] == {"deleted": 0}
