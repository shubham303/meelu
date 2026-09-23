import numpy as np

from tests.conftest import TEST_URL
from tests.integration.seo.test_rollup import BASE, BLOG, HOME, PRICING, prepare, vector
from tests.integration.site_structure.test_removals_and_pillars import seed_embedded_chunk


class FakeEmbedder:
    def embed(self, texts):
        out = []
        for t in texts:
            if "espresso" in t or "grinder" in t:
                out.append(vector(1))
            elif "acme" in t:
                out.append(vector(3))
            else:
                out.append(vector(7))
        return out


def test_psycopg_sql_rewrites_named_parameters():
    from src.seo.precompute.clusters import psycopg_sql

    assert psycopg_sql("where a = :site_id and b = cast(:ids as text[]) and c::text = 'x'") == (
        "where a = %(site_id)s and b = cast(%(ids)s as text[]) and c::text = 'x'"
    )


async def test_worker_pass_builds_clusters_and_owner(client, email, monkeypatch):
    from src.embed_worker.db import Db
    from src.seo.precompute import clusters

    site, user_id, pages = await prepare(client, email)
    await seed_embedded_chunk(site["id"], user_id, pages[PRICING], vector(1), "Espresso machines")
    await seed_embedded_chunk(site["id"], user_id, pages[BLOG], vector(2), "Beans")
    await seed_embedded_chunk(site["id"], user_id, pages[HOME], vector(3), "Acme")

    from sqlalchemy import text

    from src.core.database import SessionLocal

    async with SessionLocal() as db:
        await db.execute(
            text("update site_chunks set ordinal = 0 where page_id = any(cast(:ids as text[]))"),
            {"ids": [pages[PRICING], pages[HOME]]},
        )
        await db.execute(
            text(
                "insert into site_page_llm_extraction (id, user_id, site_id, page_id, page_type, "
                "confidence, extracted_at) values ('x1', :u, :s, :p, 'money', 0.9, now())"
            ),
            {"p": pages[PRICING], "u": user_id, "s": site["id"]},
        )
        await db.commit()

    r = await client.post(f"{BASE}/rollup")
    assert r.status_code == 200
    r = await client.post(f"{BASE}/jobs", json={"prompt": "seed"})
    job = r.json()["data"]
    r = await client.post(
        f"{BASE}/page-suggestions",
        json={
            "jobId": job["id"],
            "action": "add",
            "topicKey": "grinder guide",
            "suggestion": "x",
            "terms": ["grinder guide", "best grinder"],
        },
    )
    assert r.status_code == 201
    r = await client.post(f"{BASE}/precompute")
    assert r.json()["data"]["precomputeRequestedAt"]

    worker_db = Db(TEST_URL)
    try:
        assert not [c for c in worker_db.missing_columns() if c.startswith("seo_keywords")]
        rebuilt = clusters.run_seo_pass(worker_db, FakeEmbedder(), "fake-model")
    finally:
        worker_db.close()
    assert rebuilt == 1

    state = (await client.get(f"{BASE}/state")).json()["data"]
    assert state["embeddedAt"]

    clusters_rows = (await client.get(f"{BASE}/clusters")).json()["data"]
    assert len(clusters_rows) >= 2
    keywords = {
        k["keyword"]: k
        for k in (await client.get(f"{BASE}/keywords", params={"page_size": 50})).json()["data"]
    }
    assert keywords["espresso machine"]["clusterId"] == keywords["grinder guide"]["clusterId"]
    assert keywords["espresso machine"]["clusterId"] != keywords["acme coffee"]["clusterId"]
    espresso_cluster = next(
        c for c in clusters_rows if c["id"] == keywords["espresso machine"]["clusterId"]
    )
    assert espresso_cluster["headKeywordId"] == keywords["espresso machine"]["id"]
    assert espresso_cluster["ownerPageId"] == pages[PRICING]
    assert espresso_cluster["ownerCoverage"] > 0.5
    assert espresso_cluster["siteSimilarity"] is not None

    r = await client.post(f"{BASE}/reconcile")
    assert r.json()["data"]["pendingPrecompute"] is False

    body = (await client.get(f"{BASE}/keywords/{keywords['best grinder']['id']}/pages")).json()[
        "data"
    ]
    assert body["content"][0]["pageId"] == pages[PRICING]
    assert np.isclose(body["content"][0]["coverage"], 0.8)
