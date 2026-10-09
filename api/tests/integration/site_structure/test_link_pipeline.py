from tests.integration.site_structure.helpers import (
    BASE,
    prepare_site,
    seed_chunk,
    seed_link,
    set_page,
)
from tests.integration.technical_seo.conftest import seed_pages

ORIGIN = "https://flow.example.com"

PAGES = [
    {"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 20},
    {"url": f"{ORIGIN}/blog", "page_type": "informational", "depth": 1, "inlinks": 4},
    {"url": f"{ORIGIN}/guide", "page_type": "informational", "depth": 1, "inlinks": 3},
    {"url": f"{ORIGIN}/pricing", "page_type": "money", "depth": 1, "inlinks": 1},
]


async def prepare(client, email):
    return await prepare_site(client, email, "flow.example.com", PAGES)


def draft(job, src, dst, **extra):
    return {
        "jobId": job["id"],
        "fromPageId": src,
        "toPageId": dst,
        "suggestion": "Link it.",
        **extra,
    }


async def test_unlinked_mentions(client, email):
    site, user_id, pages, job = await prepare(client, email)
    home, blog, guide, pricing = (pages[f"{ORIGIN}/{p}"] for p in ("", "blog", "guide", "pricing"))
    await seed_chunk(site["id"], user_id, blog, 1, text_="Compare our pricing plans today.")
    await seed_chunk(site["id"], user_id, guide, 1, text_="See the Pricing Plans page.")
    await seed_chunk(site["id"], user_id, home, 1, text_="Pricing plans for everyone.")
    await seed_link(site["id"], user_id, home, pricing)

    mentions = {"jobId": job["id"], "targets": [{"toId": pricing, "phrases": ["pricing plans"]}]}
    r = await client.post(f"{BASE}/link-suggestions/mentions", json=mentions)
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 2, "skipped": 0, "targetsWithoutMatch": []}
    rows = (await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})).json()["data"]
    assert {r["fromPageId"] for r in rows} == {blog, guide}
    assert all(r["fromChunkId"] for r in rows)
    assert all('"pricing plans"' in r["suggestion"] for r in rows)

    r = await client.post(f"{BASE}/link-suggestions/mentions", json=mentions)
    assert r.json()["data"] == {"inserted": 0, "skipped": 2, "targetsWithoutMatch": []}

    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={**mentions, "targets": [{"toId": guide, "phrases": ["nothing like this"]}]},
    )
    assert r.json()["data"]["targetsWithoutMatch"] == [guide]
    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={**mentions, "targets": [{"toId": "x", "phrases": ["a"]}]},
    )
    assert r.status_code == 404
    for targets in (
        [],
        [{"toId": guide, "phrases": []}],
        [{"toId": guide, "phrases": ["a"]}, {"toId": guide, "phrases": ["b"]}],
    ):
        r = await client.post(
            f"{BASE}/link-suggestions/mentions", json={**mentions, "targets": targets}
        )
        assert r.status_code == 400, targets


async def test_mentions_phrases_stay_with_their_target(client, email):
    site, user_id, pages, job = await prepare(client, email)
    home, blog, guide, pricing = (pages[f"{ORIGIN}/{p}"] for p in ("", "blog", "guide", "pricing"))
    await seed_chunk(site["id"], user_id, home, 1, text_="Read the 100% guide on pricing tiers.")
    await seed_chunk(site["id"], user_id, blog, 1, text_="Our pricing tiers explained.")
    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={
            "jobId": job["id"],
            "targets": [
                {"toId": pricing, "phrases": ["pricing tiers"]},
                {"toId": guide, "phrases": ["100% guide", "0_guide"]},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["inserted"] == 3
    rows = (await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})).json()["data"]
    assert {(r["fromPageId"], r["toPageId"]) for r in rows} == {
        (home, pricing),
        (blog, pricing),
        (home, guide),
    }


async def test_mentions_limit_applies_per_target(client, email):
    site, user_id, pages, job = await prepare(client, email)
    pricing = pages[f"{ORIGIN}/pricing"]
    for p in ("", "blog", "guide"):
        await seed_chunk(
            site["id"], user_id, pages[f"{ORIGIN}/{p}"], 1, text_="cheap plans and costs"
        )
    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={
            "jobId": job["id"],
            "targets": [{"toId": pricing, "phrases": ["cheap plans", "costs"]}],
            "limitPerTarget": 2,
        },
    )
    assert r.json()["data"]["inserted"] == 2


async def test_screening_reads_only_drafts(client, email, screener):
    _, _, pages, job = await prepare(client, email)
    blog, guide, pricing = (pages[f"{ORIGIN}/{p}"] for p in ("blog", "guide", "pricing"))
    a = (await client.post(f"{BASE}/link-suggestions", json=draft(job, blog, pricing))).json()[
        "data"
    ]
    b = (
        await client.post(
            f"{BASE}/link-suggestions", json=draft(job, guide, pricing, state="review_approved")
        )
    ).json()["data"]

    r = await client.post(f"{BASE}/link-suggestions/screen", json={"jobId": job["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"screened": 1, "approved": 1, "rejected": 0, "failed": 0}
    row = (await client.get(f"{BASE}/link-suggestions/{a['id']}")).json()["data"]
    assert row["state"] == "screening_approved"
    assert row["confidence"] == 0.9
    assert (await client.get(f"{BASE}/link-suggestions/{b['id']}")).json()["data"][
        "state"
    ] == "review_approved"

    r = await client.post(f"{BASE}/link-suggestions/screen", json={"jobId": job["id"]})
    assert r.json()["data"]["screened"] == 0


async def test_screening_rejects_a_confident_no(client, email, rejecting_screener):
    _, _, pages, job = await prepare(client, email)
    blog, pricing = pages[f"{ORIGIN}/blog"], pages[f"{ORIGIN}/pricing"]
    a = (await client.post(f"{BASE}/link-suggestions", json=draft(job, blog, pricing))).json()[
        "data"
    ]
    r = await client.post(f"{BASE}/link-suggestions/screen", json={"ids": [a["id"]]})
    assert r.json()["data"] == {"screened": 1, "approved": 0, "rejected": 1, "failed": 0}
    row = (await client.get(f"{BASE}/link-suggestions/{a['id']}")).json()["data"]
    assert row["state"] == "screening_rejected"


async def test_review_reads_only_screening_approved_and_verdicts_move_only_those(
    client, email, screener
):
    site, user_id, pages, job = await prepare(client, email)
    blog, guide, pricing, home = (pages[f"{ORIGIN}/{p}"] for p in ("blog", "guide", "pricing", ""))
    await seed_link(site["id"], user_id, blog, home, anchor="start here")
    await seed_link(site["id"], user_id, blog, home, region="nav", anchor="Home")
    a = (await client.post(f"{BASE}/link-suggestions", json=draft(job, blog, pricing))).json()[
        "data"
    ]
    b = (await client.post(f"{BASE}/link-suggestions", json=draft(job, guide, pricing))).json()[
        "data"
    ]
    await client.post(f"{BASE}/link-suggestions/screen", json={"jobId": job["id"]})
    c = (await client.post(f"{BASE}/link-suggestions", json=draft(job, blog, guide))).json()["data"]

    r = await client.post(
        f"{BASE}/link-suggestions/review-inputs",
        json={"prompt": "Related content", "jobId": job["id"]},
    )
    assert r.status_code == 200, r.text
    batch = r.json()["data"]
    assert "Related content" in batch["instructions"]
    assert batch["schema"]["properties"]["verdict"]["enum"] == [
        "review_approved",
        "review_rejected",
    ]
    assert {item["id"] for item in batch["items"]} == {a["id"], b["id"]}
    assert all("pricing" in item["state"]["target"]["url"] for item in batch["items"])
    assert all(
        item["state"]["target"]["details"].startswith(
            "Page role: what the page is for on the site: money"
        )
        for item in batch["items"]
    )
    assert all("Page kind" in item["state"]["source"]["details"] for item in batch["items"])
    assert "read those details too" in batch["instructions"]
    from_blog = next(item for item in batch["items"] if item["id"] == a["id"])
    assert sorted(from_blog["state"]["source"]["links"], key=lambda x: x["region"]) == [
        {"url": f"{ORIGIN}/", "anchor": "start here", "region": "body"},
        {"url": f"{ORIGIN}/", "anchor": "Home", "region": "nav"},
    ]
    assert "same line" in batch["instructions"]

    r = await client.post(
        f"{BASE}/link-suggestions/verdicts",
        json={
            "verdicts": [
                {"id": a["id"], "verdict": "review_approved"},
                {"id": b["id"], "verdict": "review_rejected"},
                {"id": c["id"], "verdict": "review_approved"},
                {"id": "lks_missing", "verdict": "review_approved"},
            ]
        },
    )
    assert r.json()["data"] == {"reviewed": 2, "approved": 1, "rejected": 1, "failed": 2}
    states = {
        row["id"]: row["state"]
        for row in (await client.get(f"{BASE}/link-suggestions", params={"state": "any"})).json()[
            "data"
        ]
    }
    assert states == {a["id"]: "review_approved", b["id"]: "review_rejected", c["id"]: "draft"}

    r = await client.post(
        f"{BASE}/link-suggestions/verdicts",
        json={"verdicts": [{"id": a["id"], "verdict": "ready"}]},
    )
    assert r.status_code == 400
    r = await client.post(f"{BASE}/link-suggestions/review-inputs", json={"prompt": " "})
    assert r.status_code == 400
    assert home


async def test_rank_keeps_the_budget_and_deletes_the_rest(client, email):
    site, user_id, pages, job = await prepare(client, email)
    blog = pages[f"{ORIGIN}/blog"]
    await set_page(blog, word_count=0)
    targets = await seed_pages(
        site["id"],
        user_id,
        [{"url": f"{ORIGIN}/t{i}", "page_type": "money", "inlinks": i} for i in range(5)],
    )
    made = []
    for i in range(5):
        r = await client.post(
            f"{BASE}/link-suggestions",
            json=draft(
                job, blog, targets[f"{ORIGIN}/t{i}"], state="review_approved", searchScore=0.8
            ),
        )
        assert r.status_code == 201, r.text
        made.append(r.json()["data"]["id"])
    untouched = (
        await client.post(
            f"{BASE}/link-suggestions",
            json=draft(job, pages[f"{ORIGIN}/guide"], pages[f"{ORIGIN}/pricing"]),
        )
    ).json()["data"]

    r = await client.post(f"{BASE}/link-suggestions/rank", json={})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"scored": 5, "kept": 3, "removed": 2}
    alive = {
        row["id"]: row
        for row in (
            await client.get(f"{BASE}/link-suggestions", params={"state": "review_approved"})
        ).json()["data"]
    }
    assert len(alive) == 3
    assert all(row["score"] > 0 for row in alive.values())
    assert set(alive) == set(made[:3])
    for sid in made[3:]:
        assert (await client.get(f"{BASE}/link-suggestions/{sid}")).status_code == 404
    kept = (await client.get(f"{BASE}/link-suggestions/{untouched['id']}")).json()["data"]
    assert kept["state"] == "draft" and kept.get("score") is None

    r = await client.post(f"{BASE}/link-suggestions/rank", json={"maxPerTarget": 0})
    assert r.status_code == 400
