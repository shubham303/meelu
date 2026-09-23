from datetime import UTC, datetime, timedelta

from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

BASE = "/api/v1/seo"

ORIGIN = "https://rollup.example.com"

PRICING = f"{ORIGIN}/pricing"
BLOG = f"{ORIGIN}/blog/beans"
HOME = f"{ORIGIN}/"


def day_ago(n: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=n)).isoformat()


def gsc_days() -> list[dict]:
    days = []
    for n in range(1, 8):
        rows = [
            {
                "query": "Espresso  Machine",
                "page": PRICING,
                "clicks": 10,
                "impressions": 100,
                "position": 5,
            },
            {
                "query": "espresso machine",
                "page": BLOG,
                "clicks": 1,
                "impressions": 20 if n % 2 else 200,
                "position": 9,
            },
            {"query": "acme coffee", "page": HOME, "clicks": 30, "impressions": 60, "position": 1},
            {"query": "tiny query", "page": BLOG, "clicks": 0, "impressions": 1, "position": 40},
        ]
        days.append({"day": day_ago(n), "rows": rows})
    for n in range(30, 36):
        days.append(
            {
                "day": day_ago(n),
                "rows": [
                    {
                        "query": "espresso machine",
                        "page": PRICING,
                        "clicks": 50,
                        "impressions": 500,
                        "position": 3,
                    }
                ],
            }
        )
    return days


async def prepare(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": "rollup.example.com", "name": "R"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    pages = await seed_pages(
        site["id"],
        user_id,
        [
            {"url": HOME, "title": "Acme Coffee", "h1": ["Acme"], "kind": "home"},
            {"url": PRICING, "title": "Espresso machine pricing", "h1": ["Pricing"], "inlinks": 9},
            {
                "url": BLOG,
                "title": "Beans",
                "headings": [{"level": 2, "text": "Best espresso machine"}],
            },
            {"url": f"{ORIGIN}/gone", "title": "Gone", "status": 404},
        ],
    )
    r = await client.post("/api/v1/site/search-data/rows", json={"days": gsc_days()})
    assert r.status_code == 200, r.text
    return site, user_id, pages


async def test_rollup_builds_page_facts_keywords_and_pairs(client, email):
    _, _, pages = await prepare(client, email)

    r = await client.patch(f"{BASE}/state", json={"brandTerms": ["Acme"]})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["brandTerms"] == ["acme"]

    r = await client.post(f"{BASE}/rollup")
    assert r.status_code == 200, r.text
    result = r.json()["data"]
    assert result["pages"] == 4
    assert result["keywords"] == 2
    assert result["rollupAt"]

    r = await client.get(f"{BASE}/pages", params={"page_size": 50})
    facts = {p["url"]: p for p in r.json()["data"]}
    assert facts[HOME]["isHome"] is True
    assert facts[HOME]["impressions28D"] == 60 * 7
    assert facts[f"{ORIGIN}/gone"]["live"] is False
    assert facts[BLOG]["headings"] == ["Best espresso machine"]
    assert facts[PRICING]["h1"] == "Pricing"
    assert facts[PRICING]["firstSeenAt"]

    r = await client.get(f"{BASE}/keywords", params={"page_size": 50})
    keywords = {k["keyword"]: k for k in r.json()["data"]}
    assert set(keywords) == {"espresso machine", "acme coffee"}
    assert keywords["acme coffee"]["branded"] is True
    assert keywords["espresso machine"]["branded"] is False
    espresso = keywords["espresso machine"]
    assert espresso["impressions28D"] == 7 * 100 + 3 * 200 + 4 * 20
    assert espresso["impressionsPrev28D"] == 6 * 500
    assert espresso["impressionsLy28D"] is None
    assert espresso["firstSource"] == "gsc"

    r = await client.get(f"{BASE}/keywords/{espresso['id']}/pages")
    gsc = {g["pageId"]: g for g in r.json()["data"]["gsc"]}
    pricing = gsc[pages[PRICING]]
    blog = gsc[pages[BLOG]]
    assert pricing["position"] == 5
    assert pricing["impressions28D"] == 700
    assert round(pricing["ctr"], 2) == 0.1
    assert pricing["leaderDays90D"] == 10
    assert blog["leaderDays90D"] == 3

    r = await client.get(f"{BASE}/pages/{pages[PRICING]}/keywords")
    assert [k["keywordId"] for k in r.json()["data"]] == [espresso["id"]]

    r = await client.get(f"{BASE}/overview")
    body = r.json()["data"]
    assert body["keywords"] == 2
    assert body["keywordsWithFacts"] == 0
    assert body["state"]["rollupAt"]


async def test_rollup_is_idempotent_and_retires_gone_pages(client, email):
    _, _, pages = await prepare(client, email)
    await client.post(f"{BASE}/rollup")
    first = (await client.get(f"{BASE}/keywords")).json()["data"]

    from sqlalchemy import delete

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage

    async with SessionLocal() as db:
        await db.execute(delete(SitePage).where(SitePage.id == pages[BLOG]))
        await db.commit()

    r = await client.post(f"{BASE}/rollup")
    assert r.json()["data"]["keywords"] == 0
    second = (await client.get(f"{BASE}/keywords")).json()["data"]
    assert [k["id"] for k in first] == [k["id"] for k in second]

    facts = {
        p["url"]: p
        for p in (await client.get(f"{BASE}/pages", params={"page_size": 50})).json()["data"]
    }
    assert facts[BLOG]["live"] is False

    espresso = next(k for k in second if k["keyword"] == "espresso machine")
    r = await client.get(f"{BASE}/keywords/{espresso['id']}/pages")
    assert [g["pageId"] for g in r.json()["data"]["gsc"]] == [pages[PRICING]]


async def test_job_start_runs_rollup_and_fails_older_running_jobs(client, email):
    await prepare(client, email)
    r = await client.post(f"{BASE}/jobs", json={"prompt": "What should I do?"})
    assert r.status_code == 201, r.text
    first = r.json()["data"]
    assert first["status"] == "RUNNING"
    assert first["vendorCeilingMicros"] > 0
    assert first["reconciled"]["pendingPrecompute"] is True

    r = await client.post(f"{BASE}/jobs", json={"prompt": "Analyse competitors"})
    second = r.json()["data"]
    r = await client.get(f"{BASE}/jobs/{first['id']}")
    assert r.json()["data"]["status"] == "FAILED"

    r = await client.patch(f"{BASE}/jobs/{second['id']}", json={"status": "completed"})
    assert r.json()["data"]["status"] == "COMPLETED"

    assert (await client.get(f"{BASE}/keywords")).json()["pagination"]["total"] == 2


def vector(axis: int) -> list[float]:
    v = [0.0] * 384
    v[axis] = 1.0
    return v


async def test_embed_at_insert_computes_coverage(client, email, monkeypatch):
    from src.seo.precompute import embed as embed_module
    from tests.integration.site_structure.test_removals_and_pillars import seed_embedded_chunk

    site, user_id, pages = await prepare(client, email)
    await seed_embedded_chunk(site["id"], user_id, pages[PRICING], vector(1), "Espresso machines")
    await seed_embedded_chunk(site["id"], user_id, pages[BLOG], vector(2), "Beans")
    await seed_embedded_chunk(site["id"], user_id, pages[HOME], vector(3), "Acme")

    async def fake_embed(inputs):
        return [vector(1) if "espresso" in i else vector(3) for i in inputs]

    monkeypatch.setattr(embed_module, "embed_texts", fake_embed)

    r = await client.post(f"{BASE}/rollup")
    assert r.json()["data"]["embedded"] == 2

    espresso = next(
        k
        for k in (await client.get(f"{BASE}/keywords")).json()["data"]
        if k["keyword"] == "espresso machine"
    )
    body = (await client.get(f"{BASE}/keywords/{espresso['id']}/pages")).json()["data"]
    content = {c["pageId"]: c for c in body["content"]}
    assert content[pages[PRICING]]["coverage"] == 1.0
    assert content[pages[PRICING]]["lexicalHit"] is True
    assert content[pages[BLOG]]["coverage"] == 0.2
    assert content[pages[BLOG]]["lexicalHit"] is True
    assert content[pages[HOME]]["lexicalHit"] is False
    gsc = {g["pageId"]: g for g in body["gsc"]}
    assert gsc[pages[PRICING]]["coverage"] == 1.0
    assert gsc[pages[BLOG]]["coverage"] == 0.2

    r = await client.post(f"{BASE}/rollup")
    assert r.json()["data"]["embedded"] == 0


async def test_export_writes_csv(client, email, tmp_path, monkeypatch):
    from src.settings import settings

    monkeypatch.setattr(settings, "agent_data_dir", tmp_path)
    await prepare(client, email)
    await client.post(f"{BASE}/rollup")
    r = await client.get(f"{BASE}/export", params={"dataset": "keywords"})
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["rows"] == 2
    lines = open(body["path"]).read().splitlines()
    assert lines[0].startswith("keyword,volume,difficulty")
    assert any(line.startswith("espresso machine,") for line in lines)
    r = await client.get(f"{BASE}/export", params={"dataset": "nope"})
    assert r.status_code in (400, 422)
