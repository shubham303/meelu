from pytest import approx

from tests.integration.site_structure.helpers import (
    BASE,
    prepare_site,
    seed_chunk,
    seed_link,
    vector,
    workspace_table,
)

ORIGIN = "https://pairs.example.com"


async def test_links_from_table(client, email):
    site, user_id, pages, job = await prepare_site(
        client,
        email,
        "pairs.example.com",
        [
            {"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 4},
            {"url": f"{ORIGIN}/blog/a", "page_type": "informational", "depth": 1, "inlinks": 2},
            {"url": f"{ORIGIN}/blog/b", "page_type": "informational", "depth": 1, "inlinks": 2},
            {"url": f"{ORIGIN}/shop/m1", "page_type": "money", "depth": 1, "inlinks": 1},
            {"url": f"{ORIGIN}/shop/m2", "page_type": "money", "depth": 1, "inlinks": 1},
            {"url": f"{ORIGIN}/shop/m3", "page_type": "money", "depth": 1, "inlinks": 1},
            {"url": f"{ORIGIN}/shop/m4", "page_type": "money", "depth": 1, "inlinks": 1},
        ],
    )
    a, b, m1, m2, m3, m4 = (
        pages[f"{ORIGIN}/{p}"]
        for p in ("blog/a", "blog/b", "shop/m1", "shop/m2", "shop/m3", "shop/m4")
    )
    for axis, target in enumerate((m1, m2, m3, m4), start=1):
        await seed_chunk(site["id"], user_id, target, 0, None, "Summary", vector(axis))
    feeding = await seed_chunk(site["id"], user_id, a, 1, None, "What to feed", vector(1))
    await seed_chunk(site["id"], user_id, a, 2, None, "Bowls", vector(2, 0.1))
    await seed_chunk(site["id"], user_id, a, 3, None, "Walks", vector(10))
    await seed_link(site["id"], user_id, a, m4)

    await workspace_table(
        user_id,
        site["id"],
        "blog_to_money",
        "from_page_id text, to_page_id text, reason text",
        [
            (a, m1, "Blog to product"),
            (a, m1, None),
            (a, m2, None),
            (a, m3, None),
            (a, m4, None),
            (b, m1, None),
            (a, "pg_missing", None),
            (a, a, None),
        ],
    )
    request = {"jobId": job["id"], "sourceTable": "blog_to_money"}
    r = await client.post(f"{BASE}/link-suggestions/from-table", json={**request, "perSource": 1})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {
        "read": 8,
        "notLive": 1,
        "alreadyLinked": 1,
        "alreadySuggested": 0,
        "notEmbedded": 1,
        "belowThreshold": 1,
        "overSourceCap": 1,
        "inserted": 1,
        "skipped": 0,
        "minSimilarity": approx(0.82),
    }
    r = await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})
    [row] = r.json()["data"]
    assert (row["fromPageId"], row["toPageId"]) == (a, m1)
    assert row["fromChunkId"] == feeding
    assert row["fromChunkText"] == "What to feed"
    assert "anchor" not in row
    assert row["searchScore"] == approx(1.0)
    assert row["action"] == "create"
    assert f"{ORIGIN}/shop/m1" in row["suggestion"]
    assert "Blog to product" in row["suggestion"]

    r = await client.post(f"{BASE}/link-suggestions/from-table", json=request)
    data = r.json()["data"]
    assert (data["alreadySuggested"], data["overSourceCap"], data["inserted"]) == (1, 0, 1)

    r = await client.post(
        f"{BASE}/link-suggestions/from-table", json={**request, "minSimilarity": 0.05}
    )
    data = r.json()["data"]
    assert (data["alreadySuggested"], data["belowThreshold"], data["inserted"]) == (2, 0, 1)

    r = await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})
    assert {row["toPageId"] for row in r.json()["data"]} == {m1, m2, m3}

    r = await client.post(
        f"{BASE}/link-suggestions/from-table", json={**request, "sourceTable": "no_such"}
    )
    assert r.status_code == 400
