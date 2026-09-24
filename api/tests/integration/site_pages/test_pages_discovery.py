from tests.integration.site_pages.conftest import save_pages


def chain(n: int) -> list[dict]:
    pages = [
        {
            "url": "https://example.com/",
            "status": 200,
            "links": [{"url": "https://example.com/d1", "anchor": "1"}],
        }
    ]
    for i in range(1, n + 1):
        pages.append(
            {
                "url": f"https://example.com/d{i}",
                "status": 200,
                "links": [{"url": f"https://example.com/d{i + 1}", "anchor": str(i + 1)}],
            }
        )
    return pages


async def test_discovery_counts_orphans_unreachable_and_deep(client, site):
    pages = chain(5) + [
        {
            "url": "https://example.com/orphan",
            "status": 200,
            "inSitemap": True,
            "links": [{"url": "https://example.com/island", "anchor": "island"}],
        },
        {"url": "https://example.com/island", "status": 200, "links": []},
        {"url": "https://example.com/gone", "status": 404, "links": []},
    ]
    await save_pages(client, pages)
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200

    r = await client.get("/api/v1/site/pages/discovery")
    assert r.status_code == 200, r.text
    d = r.json()["data"]

    assert d["homeFound"] is True
    assert d["live"] == 8
    assert d["orphans"] == 1
    assert [p["url"] for p in d["orphanPages"]] == ["https://example.com/orphan"]
    assert d["orphanPages"][0]["inSitemap"] is True
    assert d["unreachable"] == 1
    assert [p["url"] for p in d["unreachablePages"]] == ["https://example.com/island"]
    assert d["deepFrom"] == 4
    assert d["deep"] == 2
    assert [p["url"] for p in d["deepPages"]] == [
        "https://example.com/d5",
        "https://example.com/d4",
    ]
    assert d["deepPages"][0]["depth"] == 5
    assert {b["depth"]: b["n"] for b in d["byDepth"]} == {
        0: 1,
        1: 1,
        2: 1,
        3: 1,
        4: 1,
        5: 1,
        None: 2,
    }


async def test_discovery_on_empty_site(client, site):
    r = await client.get("/api/v1/site/pages/discovery")
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["homeFound"] is False
    assert d["orphans"] == 0 and d["deep"] == 0 and d["unreachable"] == 0
    assert d["byDepth"] == []
