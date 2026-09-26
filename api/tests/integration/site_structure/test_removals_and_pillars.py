from datetime import UTC, datetime

from sqlalchemy import text

from tests.conftest import signup
from tests.integration.site_structure.test_link_suggestions import seed_link
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

ORIGIN = "https://pillars.example.com"

BASE = "/api/v1/site/structure"

DIMS = 384


def vector(axis: int, wobble: float = 0.0) -> list[float]:
    v = [0.0] * DIMS
    v[axis] = 1.0
    v[(axis + 1) % DIMS] = wobble
    return v


async def seed_embedded_chunk(site_id, user_id, page_id, embedding, text_="A passage") -> str:
    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.site_pages.models.site_chunk import SiteChunk

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        row = SiteChunk(
            id=uid("chn"),
            user_id=user_id,
            site_id=site_id,
            page_id=page_id,
            ordinal=1,
            text=text_,
            embedding=embedding,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        return row.id


async def workspace_table(user_id: str, name: str, columns: str, rows: list[tuple]) -> None:
    from src.agent.context import tenant_names
    from src.core.database import SessionLocal

    _, schema = tenant_names(user_id)
    async with SessionLocal() as db:
        await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await db.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{name}"'))
        await db.execute(text(f'CREATE TABLE "{schema}"."{name}" ({columns})'))
        width = len(rows[0]) if rows else 0
        marks = ", ".join(f":c{i}" for i in range(width))
        for row in rows:
            await db.execute(
                text(f'INSERT INTO "{schema}"."{name}" VALUES ({marks})'),
                {f"c{i}": v for i, v in enumerate(row)},
            )
        await db.commit()


async def prepare(client, email, pages):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": "pillars.example.com", "name": "P"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    made = await seed_pages(site["id"], user_id, pages)
    r = await client.post(f"{BASE}/jobs", json={"prompt": "Prune and pillar"})
    return site, user_id, made, r.json()["data"]


async def test_generators_revive_llm_rejected_rows(client, email):
    site, user_id, pages, job = await prepare(
        client,
        email,
        [
            {"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 4},
            {"url": f"{ORIGIN}/guide", "page_type": "informational", "depth": 1, "inlinks": 2},
        ],
    )
    home, guide = pages[f"{ORIGIN}/"], pages[f"{ORIGIN}/guide"]
    await seed_embedded_chunk(site["id"], user_id, home, vector(0), "Read the buying guide now.")
    body = {"jobId": job["id"], "toIds": [guide], "phrases": ["buying guide"]}
    r = await client.post(f"{BASE}/link-suggestions/mentions", json=body)
    assert r.json()["data"]["inserted"] == 1
    row = (await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})).json()["data"][
        0
    ]

    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={"state": "llm_rejected"})
    assert r.status_code == 200
    r = await client.post(f"{BASE}/jobs", json={"prompt": "Another strategy"})
    job2 = r.json()["data"]
    r = await client.post(f"{BASE}/link-suggestions/mentions", json={**body, "jobId": job2["id"]})
    assert r.json()["data"]["inserted"] == 1
    r = await client.get(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"]["state"] == "draft"
    assert r.json()["data"]["jobId"] == job2["id"]

    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={"state": "user_rejected"})
    r = await client.post(f"{BASE}/link-suggestions/mentions", json={**body, "jobId": job2["id"]})
    assert r.json()["data"] == {"inserted": 0, "skipped": 1, "targetsWithoutMatch": []}
    r = await client.get(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"]["state"] == "user_rejected"


async def test_link_removals(client, email, screener):
    site, user_id, pages, job = await prepare(
        client,
        email,
        [
            {"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 4},
            {
                "url": f"{ORIGIN}/blog/a",
                "page_type": "informational",
                "depth": 1,
                "inlinks": 3,
                "word_count": 900,
            },
            {"url": f"{ORIGIN}/blog/b", "page_type": "informational", "depth": 1, "inlinks": 3},
            {"url": f"{ORIGIN}/legal", "page_type": "utility", "depth": 1, "inlinks": 1},
        ],
    )
    home, a, b, legal = (pages[f"{ORIGIN}/{p}"] for p in ("", "blog/a", "blog/b", "legal"))
    await seed_link(site["id"], user_id, a, b)
    await seed_link(site["id"], user_id, home, b)
    await seed_link(site["id"], user_id, a, legal)
    await seed_link(site["id"], user_id, a, home, region="nav")
    await seed_link(site["id"], user_id, b, a)
    await seed_link(site["id"], user_id, home, a)
    await seed_embedded_chunk(site["id"], user_id, a, vector(0), "Our terms of use are strict.")
    await seed_embedded_chunk(site["id"], user_id, b, vector(5))

    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page_link import SitePageLink

    async with SessionLocal() as db:
        await db.execute(
            update(SitePageLink)
            .where(SitePageLink.src_page_id == a, SitePageLink.dst_page_id == b)
            .values(anchor="terms of use")
        )
        await db.commit()

    await workspace_table(
        user_id,
        "prune",
        "from_page_id text, to_page_id text, reason text",
        [
            (a, b, "Generic anchor"),
            (a, legal, None),
            (a, home, None),
            (home, b, None),
            (a, "pg_missing", None),
        ],
    )

    r = await client.post(
        f"{BASE}/link-suggestions/removals", json={"jobId": job["id"], "sourceTable": "prune"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {
        "read": 5,
        "inserted": 2,
        "skipped": 0,
        "notBodyLinks": 1,
        "lastInlink": 1,
        "toHubOrHome": 0,
    }

    r = await client.get(f"{BASE}/link-suggestions", params={"state": "draft", "action": "delete"})
    rows = {(row["fromPageId"], row["toPageId"]): row for row in r.json()["data"]}
    assert set(rows) == {(a, b), (home, b)}
    assert "Generic anchor" in rows[(a, b)]["suggestion"]
    assert rows[(a, b)]["fromChunkId"] is not None
    assert rows[(a, b)]["searchScore"] is not None and rows[(a, b)]["searchScore"] < 0.5
    assert rows[(home, b)].get("searchScore") is None

    r = await client.post(
        f"{BASE}/link-suggestions/removals", json={"jobId": job["id"], "sourceTable": "prune"}
    )
    assert r.json()["data"]["inserted"] == 0
    r = await client.post(
        f"{BASE}/link-suggestions/removals", json={"jobId": job["id"], "sourceTable": "no such"}
    )
    assert r.status_code == 400

    r = await client.post(f"{BASE}/link-suggestions/rank", json={})
    assert r.json()["data"]["scored"] == 2
    r = await client.get(f"{BASE}/link-suggestions/{rows[(a, b)]['id']}")
    assert r.json()["data"]["score"] is not None

    async with SessionLocal() as db:
        from sqlalchemy import delete

        await db.execute(
            delete(SitePageLink).where(SitePageLink.src_page_id == a, SitePageLink.dst_page_id == b)
        )
        await db.commit()
    r = await client.post(f"{BASE}/link-suggestions/reconcile")
    assert r.json()["data"] == {"done": 0, "stale": 0, "removed": 1}
    r = await client.get(f"{BASE}/link-suggestions/{rows[(a, b)]['id']}")
    assert r.status_code == 404


async def test_pillar_pages(client, email, screener):
    urls = [f"{ORIGIN}/seo/{i}" for i in range(5)] + [f"{ORIGIN}/ads/{i}" for i in range(4)]
    site, user_id, pages, job = await prepare(
        client,
        email,
        [{"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 9}]
        + [
            {
                "url": u,
                "page_type": "informational",
                "depth": 1,
                "inlinks": 2,
                "title": u.rsplit("/", 2)[1] + " tips",
            }
            for u in urls
        ],
    )
    seo = [pages[u] for u in urls[:5]]
    ads = [pages[u] for u in urls[5:]]
    home = pages[f"{ORIGIN}/"]
    for i, p in enumerate(seo):
        await seed_embedded_chunk(site["id"], user_id, p, vector(0, 0.05 * i))
    for i, p in enumerate(ads):
        await seed_embedded_chunk(site["id"], user_id, p, vector(9, 0.05 * i))
    partial = [0.0] * DIMS
    partial[9] = 1.0
    partial[20] = 1.5
    await seed_embedded_chunk(site["id"], user_id, home, partial)
    for p in ads[:3]:
        await seed_link(site["id"], user_id, home, p)

    await workspace_table(
        user_id,
        "folders",
        "group_key text, page_id text, topic text",
        [("ads", p, "Paid ads") for p in ads] + [("tiny", seo[0], None), ("tiny", seo[1], None)],
    )
    r = await client.post(
        f"{BASE}/pillar-suggestions/propose",
        json={"jobId": job["id"], "sourceTable": "folders", "minSize": 3},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["groups"] == 2
    assert data["tooSmall"] == 1
    assert data["inserted"] == 1
    r = await client.get(
        f"{BASE}/pillar-suggestions", params={"state": "draft", "action": "expand"}
    )
    expand = r.json()["data"][0]
    assert expand["coveringPageId"] == home
    assert expand["coveringUrl"] == f"{ORIGIN}/"
    assert expand["topic"] == "Paid ads"
    assert "Expand" in expand["suggestion"]

    r = await client.post(f"{BASE}/pillar-suggestions/propose", json={"jobId": job["id"]})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["groups"] == 2
    assert data["inserted"] == 1
    assert data["overlapsOpen"] == 1

    r = await client.get(
        f"{BASE}/pillar-suggestions", params={"state": "draft", "action": "create"}
    )
    rows = r.json()["data"]
    assert len(rows) == 1
    row = rows[0]
    assert set(row["memberPageIds"]) == set(seo)
    assert "seo" in row["topic"].split(", ")
    assert len(row["members"]) == 5
    assert row["searchScore"] > 0.9

    r = await client.post(f"{BASE}/pillar-suggestions/propose", json={"jobId": job["id"]})
    assert r.json()["data"]["overlapsOpen"] == 2

    r = await client.post(f"{BASE}/pillar-suggestions/screen", json={"jobId": job["id"]})
    assert r.json()["data"]["screened"] == 2
    assert r.json()["data"]["llmRejected"] == 0

    r = await client.post(
        f"{BASE}/pillar-suggestions/review-inputs", json={"prompt": "Pillars", "jobId": job["id"]}
    )
    batch = r.json()["data"]
    assert "Pillars" in batch["instructions"]
    assert len(batch["items"]) == 2
    verdicts = [
        {
            "id": item["id"],
            "verdict": "ready" if item["state"]["action"] == "create" else "llm_rejected",
            "title": "The SEO hub",
            "suggestion": "Build it.",
        }
        for item in batch["items"]
    ]

    r = await client.post(f"{BASE}/pillar-suggestions/verdicts", json={"verdicts": verdicts})
    assert r.json()["data"] == {"reviewed": 2, "ready": 1, "llmRejected": 1, "failed": 0}
    r = await client.get(f"{BASE}/pillar-suggestions/{row['id']}")
    assert r.json()["data"]["state"] == "ready"
    assert r.json()["data"]["topic"] == "The SEO hub"
    assert r.json()["data"]["suggestion"] == "Build it."

    r = await client.post(f"{BASE}/pillar-suggestions/rank", json={"budget": 1})
    assert r.json()["data"] == {"scored": 1, "kept": 1, "llmRejected": 0}
    r = await client.get(f"{BASE}/pillar-suggestions/summary")
    assert r.json()["data"] == {
        "draft": 0,
        "ready": 1,
        "llmRejected": 1,
        "userRejected": 0,
        "done": 0,
        "stale": 0,
    }

    hub = await seed_pages(
        site["id"],
        user_id,
        [{"url": f"{ORIGIN}/seo/", "page_type": "utility", "depth": 1, "inlinks": 1}],
    )
    for p in seo[:4]:
        await seed_link(site["id"], user_id, hub[f"{ORIGIN}/seo/"], p)
    r = await client.post(f"{BASE}/jobs", json={"prompt": "Next run"})
    assert r.json()["data"]["reconciled"] == {"done": 1, "stale": 0, "removed": 0}
    r = await client.get(f"{BASE}/pillar-suggestions/{row['id']}")
    assert r.json()["data"]["state"] == "done"

    r = await client.patch(
        f"{BASE}/pillar-suggestions/{row['id']}", json={"state": "user_rejected"}
    )
    assert r.json()["data"]["state"] == "user_rejected"
    r = await client.delete(f"{BASE}/pillar-suggestions/{row['id']}")
    assert r.json()["data"] == {"id": row["id"], "deleted": True}
    r = await client.get(f"{BASE}/pillar-suggestions/{row['id']}")
    assert r.status_code == 404
