from tests.integration.site_structure.helpers import (
    BASE,
    drop_links,
    prepare_site,
    seed_chunk,
    seed_link,
    set_page,
)
from tests.integration.technical_seo.conftest import seed_pages

ORIGIN = "https://links.example.com"

PAGES = [
    {"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 40},
    {"url": f"{ORIGIN}/blog/how-to", "page_type": "informational", "depth": 2, "inlinks": 5},
    {"url": f"{ORIGIN}/pricing", "page_type": "money", "depth": 1, "inlinks": 1},
    {"url": f"{ORIGIN}/features", "page_type": "money", "depth": 1, "inlinks": 2},
]


async def prepare(client, email):
    site, user_id, pages, job = await prepare_site(client, email, "links.example.com", PAGES)
    blog = pages[f"{ORIGIN}/blog/how-to"]
    chunks = [await seed_chunk(site["id"], user_id, blog, i, f"Section {i}") for i in (1, 2)]
    return site, user_id, pages, chunks, job


def body(job, **extra):
    return {
        "jobId": job["id"],
        "fromUrl": f"{ORIGIN}/blog/how-to",
        "toUrl": f"{ORIGIN}/pricing",
        "suggestion": "The how-to article never links to pricing.",
        **extra,
    }


async def test_create_get_update_delete(client, email):
    _, _, pages, chunks, job = await prepare(client, email)
    blog, pricing = pages[f"{ORIGIN}/blog/how-to"], pages[f"{ORIGIN}/pricing"]

    r = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[0]))
    assert r.status_code == 201, r.text
    row = r.json()["data"]
    assert row["state"] == "draft"
    assert (row["fromPageId"], row["toPageId"]) == (blog, pricing)
    assert row["fromUrl"] == f"{ORIGIN}/blog/how-to"
    assert row["toUrl"] == f"{ORIGIN}/pricing"
    assert row["fromChunkHeading"] == "Section 1"
    assert row["fromChunkOrdinal"] == 1

    r = await client.get(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"]["id"] == row["id"]

    r = await client.patch(
        f"{BASE}/link-suggestions/{row['id']}",
        json={"state": "user_rejected", "suggestion": "Not now."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["state"] == "user_rejected"
    assert r.json()["data"]["suggestion"] == "Not now."

    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={"state": "ready"})
    assert r.status_code == 400
    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={})
    assert r.status_code == 400
    r = await client.patch(f"{BASE}/link-suggestions/lks_missing", json={"state": "draft"})
    assert r.status_code == 404

    r = await client.delete(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"] == {"id": row["id"], "deleted": True}
    r = await client.get(f"{BASE}/link-suggestions/{row['id']}")
    assert r.status_code == 404
    r = await client.delete(f"{BASE}/link-suggestions/{row['id']}")
    assert r.status_code == 404


async def test_create_validates_pages_chunks_and_links(client, email):
    site, user_id, pages, chunks, job = await prepare(client, email)
    blog, pricing, home = (pages[f"{ORIGIN}/{p}"] for p in ("blog/how-to", "pricing", ""))
    other_chunk = await seed_chunk(site["id"], user_id, pricing, 1, "Elsewhere")

    r = await client.post(f"{BASE}/link-suggestions", json=body(job, toUrl=f"{ORIGIN}/blog/how-to"))
    assert r.status_code == 400
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, toUrl=f"{ORIGIN}/nowhere"))
    assert r.status_code == 404
    r = await client.post(
        f"{BASE}/link-suggestions", json=body(job, toUrl=None, toPageId="spg_missing")
    )
    assert r.status_code == 404
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, jobId="sjb_missing"))
    assert r.status_code == 404
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=other_chunk))
    assert r.status_code == 400
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId="chn_missing"))
    assert r.status_code == 404

    await set_page(pricing, status=404)
    r = await client.post(f"{BASE}/link-suggestions", json=body(job))
    assert r.status_code == 400
    await set_page(pricing, status=200)

    await seed_link(site["id"], user_id, blog, pricing)
    r = await client.post(f"{BASE}/link-suggestions", json=body(job))
    assert r.status_code == 409
    r = await client.post(
        f"{BASE}/link-suggestions",
        json=body(job, toUrl=f"{ORIGIN}/", action="delete"),
    )
    assert r.status_code == 400
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, action="delete"))
    assert r.status_code == 201, r.text
    assert home


async def test_duplicates_follow_the_chunk_rule(client, email):
    _, _, _, chunks, job = await prepare(client, email)
    first = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[0]))
    assert first.status_code == 201, first.text

    r = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[0]))
    assert r.status_code == 409
    assert first.json()["data"]["id"] in r.json()["error"]["message"]

    second = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[1]))
    assert second.status_code == 201, second.text

    r = await client.post(f"{BASE}/link-suggestions", json=body(job))
    assert r.status_code == 409

    r = await client.patch(
        f"{BASE}/link-suggestions/{second.json()['data']['id']}", json={"fromChunkId": chunks[0]}
    )
    assert r.status_code == 409
    r = await client.patch(
        f"{BASE}/link-suggestions/{second.json()['data']['id']}", json={"fromChunkId": None}
    )
    assert r.status_code == 409

    r = await client.delete(f"{BASE}/link-suggestions/{first.json()['data']['id']}")
    r = await client.patch(
        f"{BASE}/link-suggestions/{second.json()['data']['id']}", json={"fromChunkId": None}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"].get("fromChunkId") is None


async def test_rejected_rows_block_the_same_suggestion(client, email):
    _, _, _, chunks, job = await prepare(client, email)
    row = (
        await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[0]))
    ).json()["data"]
    await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={"state": "user_rejected"})
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[0]))
    assert r.status_code == 409
    r = await client.post(f"{BASE}/link-suggestions", json=body(job, fromChunkId=chunks[1]))
    assert r.status_code == 201


async def test_list_states_filters_and_summary(client, email):
    _, _, pages, chunks, job = await prepare(client, email)
    made = {}
    for state, target in (
        ("draft", "pricing"),
        ("review_approved", "features"),
        ("user_rejected", ""),
    ):
        r = await client.post(
            f"{BASE}/link-suggestions",
            json=body(job, toUrl=f"{ORIGIN}/{target}", state=state),
        )
        assert r.status_code == 201, r.text
        made[state] = r.json()["data"]["id"]

    async def ids(**params):
        r = await client.get(f"{BASE}/link-suggestions", params=params)
        assert r.status_code == 200, r.text
        return {row["id"] for row in r.json()["data"]}

    assert await ids() == {made["review_approved"], made["user_rejected"]}
    assert await ids(state="any") == set(made.values())
    assert await ids(state="draft") == {made["draft"]}
    assert await ids(state=["draft", "user_rejected"]) == {made["draft"], made["user_rejected"]}
    r = await client.get(f"{BASE}/link-suggestions", params={"state": "ready"})
    assert r.status_code == 400

    assert await ids(state="any", url="/pricing") == {made["draft"]}
    assert await ids(state="any", url="how-to") == set(made.values())
    assert await ids(state="any", toUrl="features") == {made["review_approved"]}
    assert await ids(state="any", fromUrl="features") == set()
    assert await ids(state="any", pageId=pages[f"{ORIGIN}/features"]) == {made["review_approved"]}
    assert await ids(state="any", jobId=job["id"], action="create") == set(made.values())
    r = await client.get(f"{BASE}/link-suggestions", params={"action": "edit"})
    assert r.status_code == 400

    r = await client.get(f"{BASE}/link-suggestions/summary")
    assert r.json()["data"] == {
        "draft": 1,
        "screeningRejected": 0,
        "screeningApproved": 0,
        "reviewApproved": 1,
        "reviewRejected": 0,
        "userRejected": 1,
    }


async def test_list_sorts(client, email):
    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.site_structure.models.link_suggestion import LinkSuggestion

    _, _, _, _, job = await prepare(client, email)
    made = {}
    for target, search, confidence in (
        ("pricing", 0.2, 0.9),
        ("features", 0.8, 0.1),
        ("", 0.5, None),
    ):
        r = await client.post(
            f"{BASE}/link-suggestions",
            json=body(job, toUrl=f"{ORIGIN}/{target}", searchScore=search),
        )
        made[r.json()["data"]["id"]] = confidence
    async with SessionLocal() as db:
        for sid, confidence in made.items():
            await db.execute(
                update(LinkSuggestion).where(LinkSuggestion.id == sid).values(confidence=confidence)
            )
        await db.commit()

    async def listed(**params):
        r = await client.get(f"{BASE}/link-suggestions", params={"state": "any", **params})
        assert r.status_code == 200, r.text
        return r.json()["data"]

    assert [r["searchScore"] for r in await listed(sortBy="searchScore")] == [0.8, 0.5, 0.2]
    assert [r["searchScore"] for r in await listed(sortBy="searchScore", sortOrder="asc")] == [
        0.2,
        0.5,
        0.8,
    ]
    assert [r.get("confidence") for r in await listed(sortBy="confidence")] == [0.9, 0.1, None]
    assert [r.get("confidence") for r in await listed(sortBy="confidence", sortOrder="asc")] == [
        0.1,
        0.9,
        None,
    ]
    r = await client.get(f"{BASE}/link-suggestions", params={"sortBy": "nope"})
    assert r.status_code == 400


async def test_reconcile_deletes_invalid_rows(client, email):
    site, user_id, pages, _, job = await prepare(client, email)
    blog, pricing, features, home = (
        pages[f"{ORIGIN}/{p}"] for p in ("blog/how-to", "pricing", "features", "")
    )
    await seed_link(site["id"], user_id, blog, home)
    added = (await client.post(f"{BASE}/link-suggestions", json=body(job))).json()["data"]
    removal = (
        await client.post(
            f"{BASE}/link-suggestions", json=body(job, toUrl=f"{ORIGIN}/", action="delete")
        )
    ).json()["data"]
    gone = (
        await client.post(
            f"{BASE}/link-suggestions",
            json=body(job, toUrl=f"{ORIGIN}/features", state="user_rejected"),
        )
    ).json()["data"]
    keep = (
        await client.post(
            f"{BASE}/link-suggestions",
            json=body(job, fromUrl=f"{ORIGIN}/features", toUrl=f"{ORIGIN}/pricing"),
        )
    ).json()["data"]

    r = await client.post(f"{BASE}/link-suggestions/reconcile")
    assert r.json()["data"] == {"removed": 0}

    await seed_link(site["id"], user_id, blog, pricing)
    await drop_links(blog, home)
    await set_page(features, status=404)
    r = await client.post(f"{BASE}/link-suggestions/reconcile")
    assert r.json()["data"] == {"removed": 4}
    for row in (added, removal, gone, keep):
        assert (await client.get(f"{BASE}/link-suggestions/{row['id']}")).status_code == 404


async def test_hierarchy_links(client, email):
    site, user_id, pages, job = await prepare_site(
        client,
        email,
        "tree.example.com",
        [
            {"url": "https://tree.example.com/", "page_type": "money", "depth": 0},
            {"url": "https://tree.example.com/blog", "page_type": "hub", "depth": 1},
            {"url": "https://tree.example.com/blog/guides", "page_type": "hub", "depth": 2},
            {"url": "https://tree.example.com/login", "page_type": "utility", "depth": 1},
            {"url": "https://tree.example.com/post", "page_type": "informational", "depth": 1},
        ],
    )
    home, blog, guides = (
        pages[f"https://tree.example.com/{p}"] for p in ("", "blog", "blog/guides")
    )
    await seed_link(site["id"], user_id, blog, guides)

    r = await client.post(f"{BASE}/link-suggestions/hierarchy", json={"jobId": job["id"]})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["homeFound"] is True
    assert data["hubs"] == 2
    assert data["inserted"] + data["skipped"] == 4
    assert data["skipped"] == 1

    rows = (await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})).json()["data"]
    pairs = {(r["fromPageId"], r["toPageId"]) for r in rows}
    assert (blog, guides) not in pairs
    assert (guides, blog) in pairs
    assert (home, blog) not in pairs and (blog, home) not in pairs
    post = pages["https://tree.example.com/post"]
    assert not any(post in pair for pair in pairs)
    assert all(r.get("fromChunkId") is None for r in rows)

    r = await client.post(f"{BASE}/link-suggestions/hierarchy", json={"jobId": job["id"]})
    assert r.json()["data"]["inserted"] == 0
    r = await client.post(f"{BASE}/link-suggestions/hierarchy", json={"jobId": "sjb_missing"})
    assert r.status_code == 404
    r = await client.post(f"{BASE}/link-suggestions/hierarchy", json={})
    assert r.status_code == 400


async def test_create_many_applies_every_rule_in_one_batch(client, email):
    from src.core.database import unit_of_work
    from src.site_structure.links.schemas import LinkAction, NewLinkSuggestion
    from src.site_structure.links.service import link_suggestion_service

    site, user_id, pages, chunks, job = await prepare(client, email)
    blog, pricing, features, home = (
        pages[f"{ORIGIN}/{p}"] for p in ("blog/how-to", "pricing", "features", "")
    )
    extra = await seed_pages(
        site["id"], user_id, [{"url": f"{ORIGIN}/contact"}, {"url": f"{ORIGIN}/about"}]
    )
    contact, about = extra[f"{ORIGIN}/contact"], extra[f"{ORIGIN}/about"]
    await seed_link(site["id"], user_id, blog, features)
    await set_page(features, word_count=0)
    for target in ("pricing", "blog/how-to", ""):
        r = await client.post(
            f"{BASE}/link-suggestions",
            json=body(
                job,
                fromUrl=f"{ORIGIN}/features",
                toUrl=f"{ORIGIN}/{target}",
                state="review_approved",
            ),
        )
        assert r.status_code == 201, r.text

    def row(src, dst, chunk=None, action=LinkAction.CREATE):
        return NewLinkSuggestion(
            job_id=job["id"],
            from_page_id=src,
            to_page_id=dst,
            from_chunk_id=chunk,
            action=action,
            suggestion="s",
        )

    rows = [
        row(blog, blog),
        row(blog, "spg_missing"),
        row(blog, features),
        row(blog, home, action=LinkAction.DELETE),
        row(blog, pricing, chunks[0]),
        row(blog, pricing, chunks[0]),
        row(blog, pricing, chunks[1]),
        row(blog, pricing),
        row(pricing, blog, chunks[0]),
        row(features, contact),
        row(about, contact),
        row(blog, features, action=LinkAction.DELETE),
    ]
    async with unit_of_work() as db:
        inserted = await link_suggestion_service.create_many(db, user_id, site["id"], rows)
    assert inserted == 4

    listed = (await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})).json()[
        "data"
    ]
    keys = {(r["fromPageId"], r["toPageId"], r["action"], r.get("fromChunkId")) for r in listed}
    assert keys == {
        (blog, pricing, "create", chunks[0]),
        (blog, pricing, "create", chunks[1]),
        (blog, features, "delete", None),
        (about, contact, "create", None),
    }
