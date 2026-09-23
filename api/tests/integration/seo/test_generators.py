from datetime import UTC, datetime, timedelta

from tests.conftest import signup
from tests.integration.seo.test_rollup import BASE
from tests.integration.seo.test_suggestions import age_pages
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

ORIGIN = "https://gen.example.com"
GUIDE = f"{ORIGIN}/guide"
RIVAL = f"{ORIGIN}/blog/guide-copy"
PRODUCT = f"{ORIGIN}/product"
FAQ = f"{ORIGIN}/faq"


def day_ago(n: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=n)).isoformat()


def row(query, page, clicks, impressions, position):
    return {
        "query": query,
        "page": page,
        "clicks": clicks,
        "impressions": impressions,
        "position": position,
    }


def gsc_days():
    days = []
    for n in range(1, 29):
        alternating = GUIDE if n % 2 else RIVAL
        other = RIVAL if n % 2 else GUIDE
        days.append(
            {
                "day": day_ago(n),
                "rows": [
                    row("grinder guide", alternating, 3, 60, 4),
                    row("grinder guide", other, 1, 20, 7),
                    row("burr grinder settings", GUIDE, 0, 40, 8),
                    row("how to clean a grinder", FAQ, 1, 30, 9),
                    row("why is my grinder loud", FAQ, 1, 30, 11),
                    row("what grinder size for espresso", FAQ, 1, 30, 12),
                    row("coffee product", PRODUCT, 1, 100, 2),
                    row("buy grinder", PRODUCT, 0, 200, 3),
                ],
            }
        )
    for n in range(29, 57):
        days.append({"day": day_ago(n), "rows": [row("coffee product", PRODUCT, 10, 100, 2)]})
    return days


async def prepare(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": "gen.example.com", "name": "G"})
    site = r.json()["data"]
    pages = await seed_pages(
        site["id"],
        user_id,
        [
            {"url": f"{ORIGIN}/", "title": "Home", "inlinks": 20},
            {"url": GUIDE, "title": "Grinder guide", "inlinks": 5, "word_count": 1500},
            {"url": RIVAL, "title": "Grinder guide copy", "inlinks": 1, "word_count": 400},
            {"url": PRODUCT, "title": "Coffee product", "meta_description": "Buy it", "inlinks": 8},
            {
                "url": FAQ,
                "title": "FAQ",
                "questions_answered": ["How to clean a grinder"],
                "inlinks": 4,
            },
        ],
    )
    days = gsc_days()
    for start in range(0, len(days), 28):
        r = await client.post(
            "/api/v1/site/search-data/rows", json={"days": days[start : start + 28]}
        )
        assert r.status_code == 200, r.text
    r = await client.post(f"{BASE}/jobs", json={"prompt": "What should I do?"})
    job = r.json()["data"]
    await age_pages(site["id"])
    return site, user_id, pages, job


async def test_page_edit_generators(client, email, monkeypatch):
    site, _, pages, job = await prepare(client, email)
    from src.seo.precompute import rollup as rollup_module

    monkeypatch.setattr(rollup_module, "CTR_MIN_SAMPLE", 1)
    await client.post(f"{BASE}/rollup")

    r = await client.post(
        f"{BASE}/page-suggestions/propose-edits",
        json={"jobId": job["id"], "evidence": "gsc", "minImpressions": 100},
    )
    assert r.status_code == 200, r.text
    gsc = r.json()["data"]
    assert gsc["drafts"] >= 1
    drafts = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "page_size": 50})
    ).json()["data"]
    by_page = {(d["pageId"], d["topicKey"]): d for d in drafts}
    assert (pages[GUIDE], "burr grinder settings") in by_page
    assert (pages[PRODUCT], "buy grinder") not in by_page

    r = await client.post(
        f"{BASE}/page-suggestions/propose-edits",
        json={"jobId": job["id"], "evidence": "questions", "minQuestions": 2},
    )
    questions = r.json()["data"]
    assert questions["drafts"] + len(questions["collided"]) == 1
    drafts = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "page_size": 50})
    ).json()["data"]
    faq = next(d for d in drafts if d["pageId"] == pages[FAQ] and "questions" in d["strategies"])
    assert faq["strategies"] == ["gsc", "questions"]
    assert set(faq["evidence"]["questions"]) == {
        "why is my grinder loud",
        "what grinder size for espresso",
    }

    r = await client.post(
        f"{BASE}/page-suggestions/propose-edits",
        json={"jobId": job["id"], "evidence": "decay", "minImpressions": 50},
    )
    assert r.json()["data"]["drafts"] == 1
    drafts = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "page_size": 50})
    ).json()["data"]
    decay = next(d for d in drafts if "decay" in d["strategies"])
    assert decay["pageId"] == pages[PRODUCT]
    assert decay["evidence"]["drop"] >= 0.9

    r = await client.post(
        f"{BASE}/page-suggestions/propose-edits",
        json={"jobId": job["id"], "evidence": "ctr", "minImpressions": 100},
    )
    ctr = r.json()["data"]
    assert ctr["drafts"] + len(ctr["collided"]) >= 1
    drafts = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "page_size": 50})
    ).json()["data"]
    low_ctr = next(d for d in drafts if "ctr" in d["strategies"])
    assert low_ctr["pageId"] == pages[PRODUCT]
    assert low_ctr["evidence"]["title"] == "Coffee product"


async def test_cannibalisation_pairs(client, email):
    site, _, pages, job = await prepare(client, email)
    r = await client.post(
        f"{BASE}/page-suggestions/propose-cannibalisation",
        json={"jobId": job["id"], "minSharedImpressions": 50},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["drafts"] == 2, r.json()
    drafts = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "page_size": 50})
    ).json()["data"]
    edit = next(d for d in drafts if d["action"] == "edit")
    delete = next(d for d in drafts if d["action"] == "delete")
    assert edit["pageId"] == pages[GUIDE]
    assert delete["pageId"] == pages[RIVAL]
    assert delete["mergeIntoPageId"] == pages[GUIDE]
    assert edit["pairId"] == delete["id"]
    assert edit["topicKey"] == "grinder guide"

    r = await client.post(
        f"{BASE}/page-suggestions/propose-cannibalisation",
        json={"jobId": job["id"], "minSharedImpressions": 50},
    )
    assert r.json()["data"]["drafts"] == 0
    assert len(r.json()["data"]["collided"]) == 2


async def test_screen_review_rank(client, email, monkeypatch):
    site, _, pages, job = await prepare(client, email)
    await client.post(
        f"{BASE}/page-suggestions/propose-cannibalisation",
        json={"jobId": job["id"], "minSharedImpressions": 50},
    )
    await client.post(
        f"{BASE}/page-suggestions/propose-edits",
        json={"jobId": job["id"], "evidence": "questions", "minQuestions": 2},
    )
    r = await client.post(
        f"{BASE}/page-suggestions",
        json={
            "jobId": job["id"],
            "action": "add",
            "topicKey": "cold brew",
            "suggestion": "Guide",
            "terms": ["cold brew"],
        },
    )
    assert r.json()["data"]["drafts"] == 1
    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.seo.models.page_suggestion import SeoPageSuggestion

    async with SessionLocal() as db:
        await db.execute(
            update(SeoPageSuggestion)
            .where(SeoPageSuggestion.topic_key == "cold brew")
            .values(state="draft")
        )
        await db.commit()

    r = await client.post(f"{BASE}/page-suggestions/screen", json={"jobId": job["id"]})
    assert r.json()["data"]["screened"] == 4, r.json()

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
            seen.append(state)
            verdict = (
                "llm_rejected"
                if state["action"] == "edit" and "questions" in state["strategies"]
                else "reviewed"
            )
            return VendorResponse(
                {
                    "model": "fake",
                    "answer": {
                        "verdict": verdict,
                        "reason": "ok",
                        "suggestion": "Rewritten brief.",
                    },
                }
            )

    monkeypatch.setattr(llm_judge, "adapters", [FakeJudge()])
    r = await client.post(
        f"{BASE}/page-suggestions/review", json={"jobId": job["id"], "prompt": "Highest return"}
    )
    body = r.json()["data"]
    assert body["reviewed"] == 1 and body["llmRejected"] == 1
    assert len(body["needsSerp"]) == 1
    assert len(seen) == 2
    pair_state = next(
        s for s in seen if s["action"] == "edit" and "cannibalisation" in s["strategies"]
    )
    assert pair_state["pair"]["action"] == "delete"
    assert pair_state["page"]["title"] == "Grinder guide"

    r = await client.post(
        f"{BASE}/page-suggestions/rank", json={"jobId": job["id"], "budgetDelete": 1}
    )
    assert r.json()["data"] == {"kept": 1, "llmRejected": 0}
    ready = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "ready", "page_size": 50})
    ).json()["data"]
    assert {d["action"] for d in ready} == {"edit", "delete"}
    assert all(d["suggestion"] == "Rewritten brief." or d["action"] == "delete" for d in ready)
    still_draft = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "page_size": 50})
    ).json()["data"]
    assert [d["topicKey"] for d in still_draft] == ["cold brew"]
