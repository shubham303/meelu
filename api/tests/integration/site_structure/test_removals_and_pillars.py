from tests.integration.site_structure.helpers import (
    BASE,
    DIMS,
    drop_links,
    prepare_site,
    seed_embedded_chunk,
    seed_link,
    set_page,
    vector,
    workspace_table,
)
from tests.integration.technical_seo.conftest import seed_pages

__all__ = ["seed_embedded_chunk"]

ORIGIN = "https://pillars.example.com"


async def prepare(client, email, pages):
    return await prepare_site(client, email, "pillars.example.com", pages)


async def test_link_removals(client, email):
    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page_link import SitePageLink

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
    removal = {"jobId": job["id"], "sourceTable": "prune"}
    r = await client.post(f"{BASE}/link-suggestions/removals", json=removal)
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
    assert rows[(a, b)]["searchScore"] > 0.5
    assert rows[(home, b)].get("searchScore") is None

    r = await client.post(f"{BASE}/link-suggestions/removals", json=removal)
    assert r.json()["data"]["inserted"] == 0
    r = await client.post(
        f"{BASE}/link-suggestions/removals", json={**removal, "sourceTable": "no such"}
    )
    assert r.status_code == 400

    for row in rows.values():
        await client.patch(
            f"{BASE}/link-suggestions/{row['id']}", json={"state": "review_approved"}
        )
    r = await client.post(f"{BASE}/link-suggestions/rank", json={})
    assert r.json()["data"]["scored"] == 2
    r = await client.get(f"{BASE}/link-suggestions/{rows[(a, b)]['id']}")
    assert r.json()["data"]["score"] is not None

    await drop_links(a, b)
    r = await client.post(f"{BASE}/link-suggestions/reconcile")
    assert r.json()["data"] == {"removed": 1}
    r = await client.get(f"{BASE}/link-suggestions/{rows[(a, b)]['id']}")
    assert r.status_code == 404


def pillar(job, members, **extra):
    return {
        "jobId": job["id"],
        "topic": "SEO",
        "memberPageIds": members,
        "suggestion": "Build a hub.",
        **extra,
    }


SIMPLE = [{"url": f"{ORIGIN}/"}] + [{"url": f"{ORIGIN}/p{i}"} for i in range(5)]


async def test_pillar_create_get_update_delete(client, email):
    site, user_id, pages, job = await prepare(client, email, SIMPLE)
    home = pages[f"{ORIGIN}/"]
    p = [pages[f"{ORIGIN}/p{i}"] for i in range(5)]

    r = await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[1], p[0], p[1]]))
    assert r.status_code == 201, r.text
    row = r.json()["data"]
    assert row["memberPageIds"] == sorted([p[0], p[1]])
    assert row["action"] == "create" and row["state"] == "draft"
    assert {m["id"] for m in row["members"]} == {p[0], p[1]}
    assert "memberKey" not in row

    r = await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[0], p[1]]))
    assert r.status_code == 409
    r = await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[0]]))
    assert r.status_code == 400
    r = await client.post(
        f"{BASE}/pillar-suggestions", json=pillar(job, [p[2], p[3]], action="expand")
    )
    assert r.status_code == 400
    r = await client.post(
        f"{BASE}/pillar-suggestions", json=pillar(job, [p[2], p[3]], coveringPageId=home)
    )
    assert r.status_code == 400
    r = await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[2], "spg_missing"]))
    assert r.status_code == 404
    await set_page(p[4], status=410)
    r = await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[2], p[4]]))
    assert r.status_code == 400

    r = await client.post(
        f"{BASE}/pillar-suggestions",
        json=pillar(
            job, [p[2], p[3]], action="expand", coveringPageId=home, state="review_approved"
        ),
    )
    assert r.status_code == 201, r.text
    expand = r.json()["data"]
    assert expand["coveringUrl"] == f"{ORIGIN}/"

    async def ids(**params):
        r = await client.get(f"{BASE}/pillar-suggestions", params=params)
        assert r.status_code == 200, r.text
        return {x["id"] for x in r.json()["data"]}

    assert await ids() == {expand["id"]}
    assert await ids(state="any") == {row["id"], expand["id"]}
    assert await ids(state="any", pageId=home) == {expand["id"]}
    assert await ids(state="any", pageId=p[0]) == {row["id"]}
    assert await ids(state="any", action="create") == {row["id"]}
    r = await client.get(f"{BASE}/pillar-suggestions", params={"state": "stale"})
    assert r.status_code == 400

    r = await client.patch(
        f"{BASE}/pillar-suggestions/{row['id']}",
        json={"topic": " Links ", "state": "user_rejected"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["topic"] == "Links"
    assert r.json()["data"]["state"] == "user_rejected"
    r = await client.get(f"{BASE}/pillar-suggestions/summary")
    assert r.json()["data"] == {
        "draft": 0,
        "screeningRejected": 0,
        "screeningApproved": 0,
        "reviewApproved": 1,
        "reviewRejected": 0,
        "userRejected": 1,
    }
    r = await client.delete(f"{BASE}/pillar-suggestions/{row['id']}")
    assert r.json()["data"] == {"id": row["id"], "deleted": True}
    assert (await client.get(f"{BASE}/pillar-suggestions/{row['id']}")).status_code == 404


async def test_pillar_reconcile_deletes_outgrown_rows(client, email):
    site, user_id, pages, job = await prepare(client, email, SIMPLE)
    home = pages[f"{ORIGIN}/"]
    p = [pages[f"{ORIGIN}/p{i}"] for i in range(5)]
    broken = (await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, p[:3]))).json()[
        "data"
    ]
    built = (
        await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[3], p[4]]))
    ).json()["data"]
    covered = (
        await client.post(
            f"{BASE}/pillar-suggestions",
            json=pillar(job, [p[0], p[4]], action="expand", coveringPageId=home),
        )
    ).json()["data"]
    keep = (await client.post(f"{BASE}/pillar-suggestions", json=pillar(job, [p[3], p[0]]))).json()[
        "data"
    ]

    r = await client.post(f"{BASE}/pillar-suggestions/reconcile")
    assert r.json()["data"] == {"removed": 0}

    await set_page(p[1], status=404)
    await set_page(p[2], status=404)
    hub = await seed_pages(site["id"], user_id, [{"url": f"{ORIGIN}/hub"}])
    await seed_link(site["id"], user_id, hub[f"{ORIGIN}/hub"], p[3])
    await seed_link(site["id"], user_id, hub[f"{ORIGIN}/hub"], p[4])
    await set_page(home, redirect_to=f"{ORIGIN}/new")

    r = await client.post(f"{BASE}/pillar-suggestions/reconcile")
    assert r.json()["data"] == {"removed": 3}
    for row in (broken, built, covered):
        assert (await client.get(f"{BASE}/pillar-suggestions/{row['id']}")).status_code == 404
    assert (await client.get(f"{BASE}/pillar-suggestions/{keep['id']}")).status_code == 200


async def test_pillar_pages_pipeline(client, email, screener):
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
    assert (data["groups"], data["tooSmall"], data["inserted"]) == (2, 1, 1)
    expand = (
        await client.get(
            f"{BASE}/pillar-suggestions", params={"state": "draft", "action": "expand"}
        )
    ).json()["data"][0]
    assert expand["coveringPageId"] == home
    assert expand["topic"] == "Paid ads"
    assert "Expand" in expand["suggestion"]

    r = await client.post(f"{BASE}/pillar-suggestions/propose", json={"jobId": job["id"]})
    data = r.json()["data"]
    assert (data["groups"], data["inserted"], data["overlapsOpen"]) == (2, 1, 1)
    row = (
        await client.get(
            f"{BASE}/pillar-suggestions", params={"state": "draft", "action": "create"}
        )
    ).json()["data"][0]
    assert set(row["memberPageIds"]) == set(seo)
    assert "seo" in row["topic"].split(", ")
    assert row["searchScore"] > 0.9

    r = await client.post(f"{BASE}/pillar-suggestions/screen", json={"jobId": job["id"]})
    assert r.json()["data"] == {"screened": 2, "approved": 2, "rejected": 0, "failed": 0}
    r = await client.post(f"{BASE}/pillar-suggestions/screen", json={"jobId": job["id"]})
    assert r.json()["data"]["screened"] == 0

    r = await client.post(
        f"{BASE}/pillar-suggestions/review-inputs", json={"prompt": "Pillars", "jobId": job["id"]}
    )
    batch = r.json()["data"]
    assert "Pillars" in batch["instructions"]
    assert batch["schema"]["properties"]["verdict"]["enum"] == [
        "review_approved",
        "review_rejected",
    ]
    assert len(batch["items"]) == 2
    verdicts = [
        {
            "id": item["id"],
            "verdict": "review_approved"
            if item["state"]["action"] == "create"
            else "review_rejected",
            "title": "The SEO hub",
            "suggestion": "Build it.",
        }
        for item in batch["items"]
    ]
    r = await client.post(
        f"{BASE}/pillar-suggestions/verdicts",
        json={"verdicts": verdicts + [{"id": "plr_missing", "verdict": "review_approved"}]},
    )
    assert r.json()["data"] == {"reviewed": 2, "approved": 1, "rejected": 1, "failed": 1}
    approved = (await client.get(f"{BASE}/pillar-suggestions/{row['id']}")).json()["data"]
    assert approved["state"] == "review_approved"
    assert approved["topic"] == "The SEO hub"
    assert approved["suggestion"] == "Build it."
    rejected = (await client.get(f"{BASE}/pillar-suggestions/{expand['id']}")).json()["data"]
    assert rejected["state"] == "review_rejected"
    assert rejected["topic"] == "Paid ads"

    r = await client.post(f"{BASE}/pillar-suggestions/propose", json={"jobId": job["id"]})
    data = r.json()["data"]
    assert (data["inserted"], data["overlapsOpen"], data["overlapsRejected"]) == (0, 1, 1)

    extra = (
        await client.post(
            f"{BASE}/pillar-suggestions",
            json=pillar(job, [ads[0], seo[0]], state="review_approved", searchScore=0.1),
        )
    ).json()["data"]
    r = await client.post(f"{BASE}/pillar-suggestions/rank", json={"budget": 1})
    assert r.json()["data"] == {"scored": 2, "kept": 1, "removed": 1}
    assert (await client.get(f"{BASE}/pillar-suggestions/{extra['id']}")).status_code == 404
    kept = (await client.get(f"{BASE}/pillar-suggestions/{row['id']}")).json()["data"]
    assert kept["score"] > 0
    r = await client.post(f"{BASE}/pillar-suggestions/rank", json={"budget": 0})
    assert r.status_code == 400
