from datetime import UTC, datetime

from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

ORIGIN = "https://links.example.com"

BASE = "/api/v1/site/structure"


async def seed_chunk(site_id, user_id, page_id, ordinal, heading, text=None) -> str:
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
            ordinal=ordinal,
            heading_path=heading,
            text=text or f"Chunk {ordinal} of {page_id}",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        return row.id


async def seed_link(site_id, user_id, src, dst, region="body") -> None:
    from sqlalchemy import select

    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage
    from src.site_pages.models.site_page_link import SitePageLink

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        dst_url = (await db.execute(select(SitePage.url).where(SitePage.id == dst))).scalar_one()
        db.add(
            SitePageLink(
                id=uid("lnk"),
                user_id=user_id,
                site_id=site_id,
                src_page_id=src,
                dst_page_id=dst,
                dst_url=dst_url,
                external=False,
                region=region,
                created_at=now,
                updated_at=now,
            )
        )
        await db.commit()


async def prepare(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": "links.example.com", "name": "Links"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    pages = await seed_pages(
        site["id"],
        user_id,
        [
            {"url": f"{ORIGIN}/", "page_type": "money", "depth": 0, "inlinks": 40},
            {
                "url": f"{ORIGIN}/blog/how-to",
                "page_type": "informational",
                "depth": 2,
                "inlinks": 5,
            },
            {"url": f"{ORIGIN}/pricing", "page_type": "money", "depth": 1, "inlinks": 1},
        ],
    )
    chunk = await seed_chunk(
        site["id"], user_id, pages[f"{ORIGIN}/blog/how-to"], 2, "Pricing tiers"
    )
    r = await client.post(f"{BASE}/jobs", json={"prompt": "Related content"})
    assert r.status_code == 201, r.text
    job = r.json()["data"]
    assert job["status"] == "RUNNING"
    assert job["reconciled"] == {"done": 0, "stale": 0}
    return site, user_id, pages, chunk, job


def suggestion(job, chunk=None, **extra):
    body = {
        "jobId": job["id"],
        "fromUrl": f"{ORIGIN}/blog/how-to",
        "toUrl": f"{ORIGIN}/pricing",
        "suggestion": "The how-to article ranks well and never links to pricing.",
    }
    if chunk:
        body["fromChunkId"] = chunk
    return {**body, **extra}


async def test_jobs(client, email):
    _, _, _, _, job = await prepare(client, email)

    r = await client.get(f"{BASE}/jobs/{job['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["prompt"] == "Related content"

    r = await client.get(f"{BASE}/jobs")
    assert r.json()["pagination"]["total"] == 1

    r = await client.patch(f"{BASE}/jobs/{job['id']}", json={"status": "completed"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "COMPLETED"

    r = await client.patch(f"{BASE}/jobs/{job['id']}", json={"status": "later"})
    assert r.status_code == 400

    r = await client.post(f"{BASE}/jobs", json={"prompt": "  "})
    assert r.status_code == 400


async def test_create_get_update_delete(client, email):
    site, user_id, pages, chunk, job = await prepare(client, email)

    r = await client.post(f"{BASE}/link-suggestions", json=suggestion(job, chunk))
    assert r.status_code == 201, r.text
    row = r.json()["data"]
    assert row["siteId"] == site["id"]
    assert row["jobId"] == job["id"]
    assert row["fromPageId"] == pages[f"{ORIGIN}/blog/how-to"]
    assert row["toPageId"] == pages[f"{ORIGIN}/pricing"]
    assert row["fromChunkId"] == chunk
    assert row["fromChunkHeading"] == "Pricing tiers"
    assert row["action"] == "create"
    assert row["state"] == "draft"
    assert row["score"] is None
    assert "userId" not in row

    r = await client.post(f"{BASE}/link-suggestions", json=suggestion(job))
    assert r.status_code == 409

    r = await client.post(f"{BASE}/link-suggestions", json=suggestion(job, action="delete"))
    assert r.status_code == 400
    home = pages[f"{ORIGIN}/"]
    await seed_link(site["id"], user_id, home, pages[f"{ORIGIN}/pricing"])
    r = await client.post(
        f"{BASE}/link-suggestions", json=suggestion(job, fromPageId=home, action="delete")
    )
    assert r.status_code == 201, r.text
    r = await client.post(
        f"{BASE}/link-suggestions", json=suggestion(job, fromPageId=home, action="create")
    )
    assert r.status_code == 409

    r = await client.post(f"{BASE}/link-suggestions", json=suggestion(job, jobId="sjb_nope"))
    assert r.status_code == 404

    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={"state": "user_rejected"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["state"] == "user_rejected"

    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={"state": "later"})
    assert r.status_code == 400

    r = await client.patch(f"{BASE}/link-suggestions/{row['id']}", json={})
    assert r.status_code == 400

    r = await client.get(f"{BASE}/link-suggestions/summary")
    assert r.json()["data"] == {
        "draft": 1,
        "ready": 0,
        "llmRejected": 0,
        "userRejected": 1,
        "done": 0,
        "stale": 0,
    }

    r = await client.get(f"{BASE}/link-suggestions", params={"state": "any", "jobId": job["id"]})
    assert r.json()["pagination"]["total"] == 2

    r = await client.delete(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"] == {"id": row["id"], "deleted": True}
    r = await client.delete(f"{BASE}/link-suggestions/{row['id']}")
    assert r.status_code == 404


async def test_reconcile_marks_done_and_stale(client, email):
    site, user_id, pages, chunk, job = await prepare(client, email)
    home, blog, pricing = (
        pages[f"{ORIGIN}/"],
        pages[f"{ORIGIN}/blog/how-to"],
        pages[f"{ORIGIN}/pricing"],
    )

    r = await client.post(f"{BASE}/link-suggestions", json=suggestion(job, chunk))
    linked = r.json()["data"]
    r = await client.post(
        f"{BASE}/link-suggestions", json=suggestion(job, fromPageId=home, toPageId=blog)
    )
    untouched = r.json()["data"]
    r = await client.post(
        f"{BASE}/link-suggestions",
        json=suggestion(job, fromPageId=pricing, toPageId=home, state="user_rejected"),
    )
    rejected = r.json()["data"]

    await seed_link(site["id"], user_id, blog, pricing)

    r = await client.post(f"{BASE}/jobs", json={"prompt": "Second run"})
    assert r.json()["data"]["reconciled"] == {"done": 1, "stale": 0}

    r = await client.get(f"{BASE}/link-suggestions/{linked['id']}")
    assert r.json()["data"]["state"] == "done"
    r = await client.get(f"{BASE}/link-suggestions/{untouched['id']}")
    assert r.json()["data"]["state"] == "draft"
    r = await client.get(f"{BASE}/link-suggestions/{rejected['id']}")
    assert r.json()["data"]["state"] == "user_rejected"

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage
    from sqlalchemy import update

    async with SessionLocal() as db:
        await db.execute(update(SitePage).where(SitePage.id == blog).values(status=404))
        await db.commit()

    r = await client.post(f"{BASE}/link-suggestions/reconcile")
    assert r.json()["data"] == {"done": 0, "stale": 1}
    r = await client.get(f"{BASE}/link-suggestions/{untouched['id']}")
    assert r.json()["data"]["state"] == "stale"


async def test_unlinked_mentions(client, email):
    site, user_id, pages, _, job = await prepare(client, email)
    home, blog, pricing = (
        pages[f"{ORIGIN}/"],
        pages[f"{ORIGIN}/blog/how-to"],
        pages[f"{ORIGIN}/pricing"],
    )
    await seed_chunk(site["id"], user_id, home, 1, "Intro", "Compare our Pricing Plans today.")
    await seed_chunk(site["id"], user_id, blog, 1, "Costs", "See the pricing plans before you buy.")
    await seed_chunk(site["id"], user_id, blog, 3, "More", "pricing plans again on the same page")
    await seed_chunk(site["id"], user_id, pricing, 1, "Self", "pricing plans on the target itself")
    await seed_link(site["id"], user_id, home, pricing)

    body = {"jobId": job["id"], "toIds": [pricing], "phrases": ["pricing plans"]}
    r = await client.post(f"{BASE}/link-suggestions/mentions", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 1, "skipped": 0, "targetsWithoutMatch": []}

    r = await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})
    rows = r.json()["data"]
    assert len(rows) == 1
    assert rows[0]["fromPageId"] == blog
    assert rows[0]["fromChunkOrdinal"] == 1
    assert "pricing plans" in rows[0]["suggestion"]

    r = await client.post(f"{BASE}/link-suggestions/mentions", json=body)
    assert r.json()["data"] == {"inserted": 0, "skipped": 1, "targetsWithoutMatch": []}

    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={"jobId": job["id"], "toIds": [home], "phrases": ["nothing says this"]},
    )
    assert r.json()["data"]["targetsWithoutMatch"] == [home]

    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={"jobId": job["id"], "toIds": ["pg_missing"], "phrases": ["x"]},
    )
    assert r.status_code == 404

    r = await client.post(
        f"{BASE}/link-suggestions/mentions",
        json={"jobId": job["id"], "toIds": [], "phrases": ["x"]},
    )
    assert r.status_code == 400


async def test_rank_scores_and_cuts_to_budget(client, email):
    site, user_id, pages, _, job = await prepare(client, email)
    home, blog, pricing = (
        pages[f"{ORIGIN}/"],
        pages[f"{ORIGIN}/blog/how-to"],
        pages[f"{ORIGIN}/pricing"],
    )
    extra = await seed_pages(
        site["id"],
        user_id,
        [
            {"url": f"{ORIGIN}/a", "inlinks": 0, "word_count": 0},
            {"url": f"{ORIGIN}/b", "inlinks": 0, "word_count": 0},
            {"url": f"{ORIGIN}/c", "inlinks": 0, "word_count": 0},
            {"url": f"{ORIGIN}/d", "inlinks": 30, "word_count": 0},
        ],
    )
    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage
    from sqlalchemy import update

    async with SessionLocal() as db:
        await db.execute(update(SitePage).where(SitePage.id == blog).values(word_count=0))
        await db.commit()

    made = {}
    for name, score in (("a", 0.9), ("b", 0.9), ("c", 0.9), ("d", 0.95)):
        r = await client.post(
            f"{BASE}/link-suggestions",
            json=suggestion(
                job, toPageId=extra[f"{ORIGIN}/{name}"], searchScore=score, state="ready"
            ),
        )
        assert r.status_code == 201, r.text
        made[name] = r.json()["data"]["id"]

    r = await client.post(f"{BASE}/link-suggestions/rank", json={})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"scored": 4, "kept": 3, "llmRejected": 1}

    r = await client.get(f"{BASE}/link-suggestions", params={"state": "any", "jobId": job["id"]})
    rows = {row["id"]: row for row in r.json()["data"]}
    assert all(0.0 <= row["score"] <= 1.0 for row in rows.values())
    assert rows[made["d"]]["state"] == "llm_rejected"
    assert {rows[made[k]]["state"] for k in "abc"} == {"ready"}
    scores = [row["score"] for row in r.json()["data"]]
    assert scores == sorted(scores, reverse=True)

    r = await client.post(f"{BASE}/link-suggestions/rank", json={"maxPerTarget": 0})
    assert r.status_code == 400


async def test_hierarchy_links(client, email):
    site, user_id, pages, _, job = await prepare(client, email)
    home = pages[f"{ORIGIN}/"]
    extra = await seed_pages(
        site["id"], user_id, [{"url": f"{ORIGIN}/blog"}, {"url": f"{ORIGIN}/blog/guides"}]
    )
    blog, guides = extra[f"{ORIGIN}/blog"], extra[f"{ORIGIN}/blog/guides"]

    from datetime import UTC, datetime

    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.site_pages.models.site_page_llm_extraction import (
        SitePageLlmExtraction,
    )

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        for pid in (blog, guides):
            db.add(
                SitePageLlmExtraction(
                    id=uid("ext"),
                    user_id=user_id,
                    site_id=site["id"],
                    page_id=pid,
                    page_type="hub",
                    extracted_from_hash="h",
                    extracted_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        await db.commit()
    await seed_link(site["id"], user_id, home, blog, region="nav")

    r = await client.post(f"{BASE}/link-suggestions/hierarchy", json={"jobId": job["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 5, "skipped": 0, "homeFound": True, "hubs": 2}

    r = await client.get(f"{BASE}/link-suggestions", params={"state": "draft"})
    edges = {(row["fromPageId"], row["toPageId"]) for row in r.json()["data"]}
    assert (home, blog) not in edges
    assert edges == {(blog, home), (home, guides), (guides, home), (blog, guides), (guides, blog)}
    assert all(row["searchScore"] is None for row in r.json()["data"])

    r = await client.post(f"{BASE}/link-suggestions/hierarchy", json={"jobId": job["id"]})
    assert r.json()["data"]["inserted"] == 0 and r.json()["data"]["skipped"] == 5


async def test_screen_then_review(client, email, monkeypatch):
    _, _, pages, chunk, job = await prepare(client, email)
    r = await client.post(f"{BASE}/link-suggestions", json=suggestion(job, chunk))
    row = r.json()["data"]

    r = await client.post(f"{BASE}/link-suggestions/screen", json={"jobId": job["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {
        "screened": 1,
        "passed": 1,
        "llmRejected": 0,
        "failed": 0,
        "stopped": None,
    }
    r = await client.get(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"]["state"] == "draft"
    assert r.json()["data"]["confidence"] == 0.9

    r = await client.post(f"{BASE}/link-suggestions/screen", json={"jobId": job["id"]})
    assert r.json()["data"]["screened"] == 0

    r = await client.post(
        f"{BASE}/link-suggestions/review", json={"prompt": "Related content", "jobId": job["id"]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["reviewed"] == 0
    assert "judge" in r.json()["data"]["stopped"]

    from src.providers.llm_judge.adapter import JUDGE, LlmJudgeAdapter
    from src.providers.llm_judge.service import llm_judge
    from src.providers.registry import VendorResponse

    seen = []

    class FakeJudge(LlmJudgeAdapter):
        id = "fake-judge"
        name = "fake"
        capabilities = frozenset({JUDGE})
        charges = False

        async def judge(self, instructions, state, schema):
            seen.append((instructions, state, schema))
            verdict = "ready" if "pricing" in state["target"]["url"] else "llm_rejected"
            return VendorResponse({"model": "fake", "answer": {"verdict": verdict, "reason": "ok"}})

    monkeypatch.setattr(llm_judge, "adapters", [FakeJudge()])

    r = await client.post(
        f"{BASE}/link-suggestions/review", json={"prompt": "Related content", "jobId": job["id"]}
    )
    assert r.json()["data"] == {
        "reviewed": 1,
        "ready": 1,
        "llmRejected": 0,
        "failed": 0,
        "stopped": None,
    }
    assert "Related content" in seen[0][0]
    assert seen[0][2]["properties"]["verdict"]["enum"] == ["ready", "llm_rejected"]
    r = await client.get(f"{BASE}/link-suggestions/{row['id']}")
    assert r.json()["data"]["state"] == "ready"

    r = await client.post(
        f"{BASE}/link-suggestions/review", json={"prompt": "Related content", "jobId": job["id"]}
    )
    assert r.json()["data"]["reviewed"] == 0

    r = await client.post(f"{BASE}/link-suggestions/review", json={"prompt": " "})
    assert r.status_code == 400
