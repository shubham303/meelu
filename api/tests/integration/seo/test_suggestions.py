from datetime import UTC, datetime, timedelta

from sqlalchemy import text, update

from tests.integration.seo.test_rollup import BASE, BLOG, HOME, ORIGIN, PRICING, prepare


async def start(client, prompt="Suggest"):
    r = await client.post(f"{BASE}/jobs", json={"prompt": prompt})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def create(client, job_id, rows):
    from sqlalchemy import select

    from src.core.database import SessionLocal
    from src.seo import suggestions
    from src.seo.models.job import SeoJob
    from src.seo.schemas import NewPageSuggestion

    async with SessionLocal() as db:
        job = (await db.execute(select(SeoJob).where(SeoJob.id == job_id))).scalar_one()
        result = await suggestions.create_many(
            db, job.user_id, job.site_id, job_id, [NewPageSuggestion(**r) for r in rows]
        )
        await db.commit()
    return result


async def set_state(suggestion_id, state):
    from src.core.database import SessionLocal
    from src.seo.models.page_suggestion import SeoPageSuggestion

    async with SessionLocal() as db:
        await db.execute(
            update(SeoPageSuggestion)
            .where(SeoPageSuggestion.id == suggestion_id)
            .values(state=state)
        )
        await db.commit()


async def age_pages(site_id, days=200):
    from src.core.database import SessionLocal

    async with SessionLocal() as db:
        await db.execute(
            text(
                "update seo_page_facts set first_seen_at = :at, clicks_28d = 0 "
                "where site_id = :site_id"
            ),
            {"at": datetime.now(UTC) - timedelta(days=days), "site_id": site_id},
        )
        await db.commit()


async def test_save_writes_ready_and_collides_on_repeat(client, email):
    _, _, pages = await prepare(client, email)
    job = await start(client)
    body = {
        "jobId": job["id"],
        "action": "edit",
        "topicKey": "Espresso Machine",
        "pageId": pages[PRICING],
        "terms": ["espresso machine", "best espresso machine"],
        "suggestion": "Add a comparison table.",
    }
    r = await client.post(f"{BASE}/page-suggestions", json=body)
    assert r.status_code == 201, r.text
    result = r.json()["data"]
    assert result["drafts"] == 1
    row = (await client.get(f"{BASE}/page-suggestions/{result['ids'][0]}")).json()["data"]
    assert row["state"] == "ready"
    assert row["topicKey"] == "espresso machine"
    assert row["strategies"] == ["agent"]
    assert row["impressionsAtCreation"] == 700
    assert (await client.get(f"{BASE}/keywords", params={"search": "best espresso"})).json()[
        "pagination"
    ]["total"] == 1

    r = await client.post(f"{BASE}/page-suggestions", json=body)
    again = r.json()["data"]
    assert again["drafts"] == 0
    assert again["collided"][0]["id"] == row["id"]

    r = await client.get(
        f"{BASE}/page-suggestions", params={"state": "ready", "pageId": pages[PRICING]}
    )
    assert r.json()["pagination"]["total"] == 1


async def test_revive_and_user_rejected_memory(client, email):
    _, _, pages = await prepare(client, email)
    job = await start(client)
    rows = [
        {
            "action": "add",
            "topic_key": "cold brew",
            "strategy": "gap",
            "suggestion": "Write cold brew guide",
        },
    ]
    first = await create(client, job["id"], rows)
    assert first.drafts == 1
    row_id = first.ids[0]

    await set_state(row_id, "llm_rejected")
    second = await create(client, job["id"], [{**rows[0], "strategy": "topic"}])
    assert second.drafts == 1 and second.ids == [row_id]
    row = (await client.get(f"{BASE}/page-suggestions/{row_id}")).json()["data"]
    assert row["state"] == "draft"
    assert row["strategies"] == ["gap", "topic"]

    r = await client.post(f"{BASE}/page-suggestions/{row_id}/reject")
    assert r.json()["data"]["state"] == "user_rejected"
    third = await create(client, job["id"], rows)
    assert third.drafts == 0
    assert third.collided[0].state == "user_rejected"


async def test_delete_protections_and_pairs(client, email):
    site, _, pages = await prepare(client, email)
    job = await start(client)
    pair = [
        {
            "action": "edit",
            "topic_key": "espresso machine",
            "page_id": pages[PRICING],
            "strategy": "cannibalisation",
            "suggestion": "Absorb",
            "pair_with": 1,
        },
        {
            "action": "delete",
            "topic_key": "espresso machine",
            "page_id": pages[BLOG],
            "merge_into_page_id": pages[PRICING],
            "strategy": "cannibalisation",
            "suggestion": "Merge into pricing",
        },
    ]
    result = await create(client, job["id"], pair)
    assert result.drafts == 0
    assert result.filtered == {"protected_young": 1, "pair_blocked": 1}

    await age_pages(site["id"])
    result = await create(client, job["id"], pair)
    assert result.drafts == 2, result
    edit_row = (await client.get(f"{BASE}/page-suggestions/{result.ids[0]}")).json()["data"]
    delete_row = (await client.get(f"{BASE}/page-suggestions/{result.ids[1]}")).json()["data"]
    assert edit_row["pairId"] == delete_row["id"]
    assert delete_row["pairId"] == edit_row["id"]

    r = await client.post(f"{BASE}/page-suggestions/{delete_row['id']}/reject")
    assert r.json()["data"]["state"] == "user_rejected"
    assert (await client.get(f"{BASE}/page-suggestions/{edit_row['id']}")).json()["data"][
        "state"
    ] == "user_rejected"

    home_delete = [
        {
            "action": "delete",
            "topic_key": "acme coffee",
            "page_id": pages[HOME],
            "merge_into_page_id": pages[PRICING],
            "strategy": "cannibalisation",
            "suggestion": "x",
        }
    ]
    assert (await create(client, job["id"], home_delete)).filtered == {"protected_type": 1}
    no_target = [
        {
            "action": "delete",
            "topic_key": "acme coffee",
            "page_id": pages[BLOG],
            "strategy": "cannibalisation",
            "suggestion": "x",
        }
    ]
    assert (await create(client, job["id"], no_target)).filtered == {"no_merge_target": 1}


async def test_reconcile_closes_rows(client, email):
    site, user_id, pages = await prepare(client, email)
    job = await start(client)
    await age_pages(site["id"])
    rows = [
        {
            "action": "edit",
            "topic_key": "espresso machine",
            "page_id": pages[PRICING],
            "strategy": "ctr",
            "suggestion": "Fix title",
            "evidence": {"title": "Espresso machine pricing", "meta_description": None},
        },
        {
            "action": "delete",
            "topic_key": "beans",
            "page_id": pages[BLOG],
            "merge_into_page_id": pages[PRICING],
            "strategy": "cannibalisation",
            "suggestion": "Merge",
        },
        {
            "action": "edit",
            "topic_key": "tiny query",
            "page_id": pages[f"{ORIGIN}/gone"],
            "strategy": "gsc",
            "suggestion": "x",
        },
    ]
    result = await create(client, job["id"], rows[:2])
    assert result.drafts == 2
    assert (await create(client, job["id"], rows[2:])).filtered == {"page_gone": 1}

    r = await client.post(f"{BASE}/reconcile")
    assert r.json()["data"] == {"done": 0, "stale": 0, "pendingPrecompute": True}

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage

    async with SessionLocal() as db:
        await db.execute(
            update(SitePage).where(SitePage.id == pages[PRICING]).values(title="New title")
        )
        await db.execute(
            update(SitePage)
            .where(SitePage.id == pages[BLOG])
            .values(status=301, redirect_to=PRICING)
        )
        await db.commit()

    await client.post(f"{BASE}/rollup")
    r = await client.post(f"{BASE}/reconcile")
    assert r.json()["data"]["done"] == 2
    states = {
        s["id"]: s["state"]
        for s in (await client.get(f"{BASE}/page-suggestions", params={"state": "any"})).json()[
            "data"
        ]
    }
    assert set(states.values()) == {"done"}
