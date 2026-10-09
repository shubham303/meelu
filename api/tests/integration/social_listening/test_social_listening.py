import psycopg
import pytest

from tests.conftest import TEST_URL, signup

PG_URL = TEST_URL.replace("postgresql+psycopg://", "postgresql://")

LONG_TEXT = (
    "Running a forty page site for a local bakery and I just want to see where we rank "
    "for about thirty keywords with an email every week."
)


def unit(axis):
    v = [0.0] * 384
    v[axis] = 1.0
    return "[" + ",".join(repr(x) for x in v) + "]"


def set_embedding(table, id, axis):
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        conn.execute(
            f"update {table} set embedding = %s::vector, embed_model = 'test' where id = %s",
            (unit(axis), id),
        )


@pytest.fixture(autouse=True)
def mount_routers():
    from src.app import app
    from src.social_listening.endpoints import router

    prefix = "/api/v1/social-listening"
    mounted = any(str(getattr(r, "path", "")).startswith(prefix) for r in app.routes)
    if not mounted:
        app.include_router(router, prefix="/api/v1")


async def prepare(client, email):
    await signup(client, email)
    r = await client.post(
        "/api/v1/sites", json={"domain": "listen.example.com", "name": "Listen Example"}
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def add_query(client, text="people asking about rank tracking"):
    r = await client.post("/api/v1/social-listening/queries", json=[{"text": text}])
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/social-listening/queries")
    return next(q["id"] for q in r.json()["data"] if q["text"] == text)


async def ingest(client, *posts, run_id=None):
    r = await client.post(
        "/api/v1/social-listening/posts/bulk", json={"runId": run_id, "posts": list(posts)}
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def all_posts(client, status=None):
    suffix = f"?status={status}&page_size=100" if status else "?page_size=100"
    r = await client.get(f"/api/v1/social-listening/posts{suffix}")
    assert r.status_code == 200, r.text
    return {p["url"]: p for p in r.json()["data"]}


async def judge(client, post_id, status="to_reply", **fields):
    r = await client.post(
        "/api/v1/social-listening/posts/judged",
        json={"posts": [{"id": post_id, "status": status, **fields}]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


def post_payload(url, **extra):
    base = {
        "url": url,
        "platform": "reddit",
        "title": "How do I automate SEO audits?",
        "text": "Looking for a tool that watches my rankings.",
        "engagement": {"score": 42, "comments": 10},
        "context": {"subreddit": "seo"},
    }
    base.update(extra)
    return base


async def test_config_lazy_create_and_update(client, email):
    await prepare(client, email)

    r = await client.get("/api/v1/social-listening/config")
    assert r.status_code == 200, r.text
    config = r.json()["data"]
    assert config["platforms"] == []
    assert config["resultsPerKeyword"] == 50
    assert config["strictness"] == "balanced"
    assert config["maxAgeDays"] == 365
    assert config["minSimilarity"] == pytest.approx(0.8)
    assert config["minRelevance"] == pytest.approx(0.6)
    assert "schedule" not in config

    r = await client.put(
        "/api/v1/social-listening/config",
        json={"strictness": "strict", "platforms": ["reddit", "hackernews"], "maxAgeDays": 45},
    )
    assert r.status_code == 200, r.text
    updated = r.json()["data"]
    assert updated["id"] == config["id"]
    assert updated["strictness"] == "strict"
    assert updated["minSimilarity"] == pytest.approx(0.85)
    assert updated["minRelevance"] == pytest.approx(0.75)
    assert updated["platforms"] == ["reddit", "hackernews"]
    assert updated["maxAgeDays"] == 45

    for bad in ({"strictness": "fierce"}, {"maxAgeDays": 0}, {"resultsPerKeyword": 0}):
        r = await client.put("/api/v1/social-listening/config", json=bad)
        assert r.status_code == 400, bad

    r = await client.get("/api/v1/social-listening/config")
    assert r.json()["data"]["maxAgeDays"] == 45


async def test_queries_upsert_patch_delete_and_counts(client, email):
    await prepare(client, email)

    r = await client.post(
        "/api/v1/social-listening/queries",
        json=[
            {"text": "people asking which tool tracks rankings"},
            {"text": "someone  frustrated their audit missed  issues", "source": "suggested"},
        ],
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 2, "updated": 0}

    r = await client.post(
        "/api/v1/social-listening/queries",
        json=[
            {"text": "people asking which tool tracks rankings", "enabled": False},
            {"text": "people talking about Meelu"},
        ],
    )
    assert r.json()["data"] == {"inserted": 1, "updated": 1}

    r = await client.get("/api/v1/social-listening/queries")
    queries = r.json()["data"]
    assert [q["text"] for q in queries] == [
        "people asking which tool tracks rankings",
        "someone frustrated their audit missed issues",
        "people talking about Meelu",
    ]
    first = queries[0]
    assert first["enabled"] is False
    assert first["embedded"] is False
    assert first["found"] == 0
    assert first["kept"] == 0

    await ingest(
        client,
        post_payload("https://reddit.com/r/seo/comments/a1/x", queryId=first["id"]),
        post_payload("https://reddit.com/r/seo/comments/a2/x", queryId=first["id"]),
        post_payload(
            "https://reddit.com/r/seo/comments/a3/x", queryId=first["id"], dropReason="too_old"
        ),
    )
    posts = await all_posts(client)
    set_embedding("social_listening_query", first["id"], 0)
    for url in ("https://reddit.com/r/seo/comments/a1/x", "https://reddit.com/r/seo/comments/a2/x"):
        set_embedding("social_listening_post", posts[url]["id"], 0)
    await client.post("/api/v1/social-listening/posts/gate")
    await judge(client, posts["https://reddit.com/r/seo/comments/a1/x"]["id"])

    r = await client.get("/api/v1/social-listening/queries")
    counted = r.json()["data"][0]
    assert counted["found"] == 3
    assert counted["kept"] == 1
    assert counted["embedded"] is True

    r = await client.patch(
        f"/api/v1/social-listening/queries/{first['id']}",
        json={"enabled": True, "keywords": ["rank tracker"], "negativeKeywords": ["job"]},
    )
    assert r.status_code == 200, r.text
    patched = r.json()["data"]
    assert patched["enabled"] is True
    assert patched["keywords"] == ["rank tracker"]
    assert patched["found"] == 3

    r = await client.patch(
        f"/api/v1/social-listening/queries/{first['id']}",
        json={"text": "people asking about rank tracking"},
    )
    assert r.json()["data"]["embedded"] is False
    assert r.json()["data"]["keywords"] == []

    r = await client.patch(f"/api/v1/social-listening/queries/{first['id']}", json={"text": "  "})
    assert r.status_code == 400

    r = await client.delete(f"/api/v1/social-listening/queries/{first['id']}")
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/social-listening/queries")
    assert len(r.json()["data"]) == 2
    r = await client.patch(
        f"/api/v1/social-listening/queries/{first['id']}", json={"enabled": True}
    )
    assert r.status_code == 404

    kept = await all_posts(client)
    assert len(kept) == 3
    assert all(p.get("queryId") is None for p in kept.values())


async def test_runs_lifecycle_and_list(client, email):
    await prepare(client, email)

    r = await client.post("/api/v1/social-listening/runs")
    assert r.status_code == 201, r.text
    run = r.json()["data"]
    assert run["status"] == "running"
    assert run["fetchedCount"] == 0
    assert run["matchedCount"] == 0
    assert run["platformStats"] == {}

    r = await client.patch(
        f"/api/v1/social-listening/runs/{run['id']}",
        json={
            "status": "done",
            "fetchedCount": 142,
            "matchedCount": 38,
            "keptCount": 20,
            "platformStats": {"reddit": {"fetched": 142, "kept": 20}},
        },
    )
    assert r.status_code == 200, r.text
    done = r.json()["data"]
    assert done["finishedAt"] is not None
    assert (done["fetchedCount"], done["matchedCount"], done["keptCount"]) == (142, 38, 20)

    r = await client.patch(f"/api/v1/social-listening/runs/{run['id']}", json={"status": "flying"})
    assert r.status_code == 400

    r = await client.post("/api/v1/social-listening/runs")
    second = r.json()["data"]
    r = await client.get("/api/v1/social-listening/runs")
    assert [x["id"] for x in r.json()["data"]] == [second["id"], run["id"]]


async def test_ingest_never_stores_the_same_post_twice(client, email):
    await prepare(client, email)
    query_id = await add_query(client)
    r = await client.post("/api/v1/social-listening/runs")
    run_id = r.json()["data"]["id"]

    result = await ingest(
        client,
        post_payload(
            "https://www.reddit.com/r/SEO/comments/abc12/what_do_you_use/?utm_source=share",
            externalId="t3_abc12",
            queryId=query_id,
            text=LONG_TEXT,
        ),
        post_payload("https://news.ycombinator.com/item?id=4242", platform="hackernews"),
        post_payload("https://old.reddit.com/r/seo/comments/ABC12/", queryId=query_id),
        run_id=run_id,
    )
    assert result == {"inserted": 2, "known": 1, "duplicates": 0}

    posts = await all_posts(client)
    rank = next(p for p in posts.values() if p["platform"] == "reddit")
    assert rank["externalId"] == "abc12"
    assert rank["status"] == "fetched"
    assert rank["runId"] == run_id

    set_embedding("social_listening_query", query_id, 0)
    set_embedding("social_listening_post", rank["id"], 0)
    await client.post("/api/v1/social-listening/posts/gate")
    await judge(client, rank["id"])
    r = await client.patch(
        f"/api/v1/social-listening/posts/{rank['id']}", json={"status": "rejected"}
    )
    assert r.status_code == 200, r.text

    variants = [
        post_payload("https://reddit.com/r/SEO/comments/abc12/", externalId="abc12"),
        post_payload("https://new.reddit.com/r/seo/comments/abc12/what_do_you_use"),
        post_payload("https://reddit.com/r/SEO/comments/abc12/x", externalId="t3_ABC12"),
    ]
    result = await ingest(client, *variants)
    assert result == {"inserted": 0, "known": 3, "duplicates": 0}

    result = await ingest(
        client,
        post_payload(
            "https://reddit.com/r/smallbusiness/comments/zz9/cross_post",
            title="How do I automate SEO audits?",
            text=LONG_TEXT,
            queryId=query_id,
        ),
    )
    assert result == {"inserted": 1, "known": 0, "duplicates": 1}

    posts = await all_posts(client)
    assert len(posts) == 3
    assert posts["https://reddit.com/r/smallbusiness/comments/zz9/cross_post"]["status"] == (
        "dropped"
    )
    assert posts["https://reddit.com/r/smallbusiness/comments/zz9/cross_post"]["dropReason"] == (
        "duplicate"
    )
    assert next(p for p in posts.values() if p["id"] == rank["id"])["status"] == "rejected"

    result = await ingest(
        client, post_payload("https://x.com/kate/status/77", platform="x", dropReason="too_old")
    )
    assert result["inserted"] == 1
    old = (await all_posts(client, "dropped"))["https://x.com/kate/status/77"]
    assert old["dropReason"] == "too_old"
    result = await ingest(
        client, post_payload("https://twitter.com/kate/status/77?s=20", platform="x")
    )
    assert result == {"inserted": 0, "known": 1, "duplicates": 0}

    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={"posts": [post_payload("https://a/1", dropReason="judged_off_topic")]},
    )
    assert r.status_code == 400
    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={"runId": "slr_missing", "posts": [post_payload("https://a/2")]},
    )
    assert r.status_code == 404


async def test_gate_and_judge_are_incremental(client, email):
    await prepare(client, email)
    query_id = await add_query(client)

    await ingest(
        client,
        post_payload("https://a.example/close", queryId=query_id),
        post_payload("https://a.example/far", queryId=query_id),
        post_payload("https://a.example/later", queryId=query_id),
        post_payload("https://a.example/orphan"),
        post_payload("https://a.example/noise", queryId=query_id, dropReason="excluded_word"),
    )
    by_url = await all_posts(client)

    r = await client.post("/api/v1/social-listening/posts/gate")
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"pending": 3, "scored": 1, "kept": 0, "dropped": 1}
    assert (await all_posts(client, "dropped"))["https://a.example/orphan"]["dropReason"] == (
        "line_removed"
    )

    set_embedding("social_listening_query", query_id, 0)
    set_embedding("social_listening_post", by_url["https://a.example/close"]["id"], 0)
    set_embedding("social_listening_post", by_url["https://a.example/far"]["id"], 1)

    r = await client.post("/api/v1/social-listening/posts/gate")
    assert r.json()["data"] == {"pending": 1, "scored": 2, "kept": 1, "dropped": 1}

    matched = await all_posts(client, "matched")
    assert list(matched) == ["https://a.example/close"]
    assert matched["https://a.example/close"]["similarity"] == pytest.approx(1.0)
    dropped = await all_posts(client, "dropped")
    assert dropped["https://a.example/far"]["dropReason"] == "far_in_meaning"
    assert dropped["https://a.example/noise"]["dropReason"] == "excluded_word"
    assert list(await all_posts(client, "fetched")) == ["https://a.example/later"]

    close_id = by_url["https://a.example/close"]["id"]
    result = await judge(
        client,
        close_id,
        relevance=0.9,
        compositeScore=0.8,
        keepReason="Asks for a tracker.",
        suggestedAngle="Answer with two free options first.",
    )
    assert result == {"updated": 1}
    r = await client.get(f"/api/v1/social-listening/posts/{close_id}")
    close = r.json()["data"]
    assert close["status"] == "to_reply"
    assert close["keepReason"] == "Asks for a tracker."
    assert close["suggestedAngle"] == "Answer with two free options first."
    assert close.get("dropReason") is None

    assert await judge(client, close_id, "dropped", dropReason="judged_off_topic") == {"updated": 0}
    r = await client.get(f"/api/v1/social-listening/posts/{close_id}")
    assert r.json()["data"]["status"] == "to_reply"

    later_id = by_url["https://a.example/later"]["id"]
    set_embedding("social_listening_post", later_id, 0)
    await client.post("/api/v1/social-listening/posts/gate")
    await judge(client, later_id, "dropped", dropReason="dead")
    assert (await all_posts(client, "dropped"))["https://a.example/later"]["dropReason"] == "dead"

    for bad in (
        {"id": close_id, "status": "drafted"},
        {"id": close_id, "status": "dropped"},
        {"id": close_id, "status": "dropped", "dropReason": "too_old"},
    ):
        r = await client.post("/api/v1/social-listening/posts/judged", json={"posts": [bad]})
        assert r.status_code == 400, bad
    r = await client.post(
        "/api/v1/social-listening/posts/judged",
        json={"posts": [{"id": "slp_missing", "status": "to_reply"}]},
    )
    assert r.status_code == 404


async def test_review_statuses_filters_and_summary(client, email):
    await prepare(client, email)
    query_id = await add_query(client)
    urls = [f"https://b.example/{n}" for n in range(5)]
    await ingest(
        client,
        *[post_payload(u, queryId=query_id, engagement={"score": i}) for i, u in enumerate(urls)],
        post_payload("https://b.example/old", queryId=query_id, dropReason="too_old"),
    )
    by_url = await all_posts(client)
    set_embedding("social_listening_query", query_id, 0)
    for u in urls:
        set_embedding("social_listening_post", by_url[u]["id"], 0)
    await client.post("/api/v1/social-listening/posts/gate")
    for i, u in enumerate(urls):
        await judge(client, by_url[u]["id"], compositeScore=i / 10)

    ids = [by_url[u]["id"] for u in urls]
    r = await client.patch(
        f"/api/v1/social-listening/posts/{ids[0]}",
        json={"status": "drafted", "replyText": "Search Console already shows this."},
    )
    assert r.status_code == 200, r.text
    r = await client.patch(f"/api/v1/social-listening/posts/{ids[1]}", json={"status": "replied"})
    assert r.json()["data"]["repliedAt"] is not None
    await client.patch(f"/api/v1/social-listening/posts/{ids[2]}", json={"status": "skipped"})
    await client.patch(f"/api/v1/social-listening/posts/{ids[3]}", json={"status": "rejected"})

    r = await client.patch(f"/api/v1/social-listening/posts/{ids[0]}", json={"status": "dropped"})
    assert r.status_code == 400
    r = await client.patch(
        f"/api/v1/social-listening/posts/{by_url['https://b.example/old']['id']}",
        json={"status": "to_reply"},
    )
    assert r.status_code == 409

    r = await client.get("/api/v1/social-listening/posts?status=replied,skipped,rejected&sort=best")
    assert [p["url"] for p in r.json()["data"]] == [urls[3], urls[2], urls[1]]
    r = await client.get("/api/v1/social-listening/posts?status=to_reply,replied&sort=engaged")
    assert [p["url"] for p in r.json()["data"]] == [urls[4], urls[1]]
    r = await client.get("/api/v1/social-listening/posts?status=nope")
    assert r.status_code == 400

    r = await client.get("/api/v1/social-listening/summary")
    summary = r.json()["data"]
    assert summary["toReply"] == 1
    assert summary["drafted"] == 1
    assert summary["replied"] == 1
    assert summary["skipped"] == 1
    assert summary["rejected"] == 1
    assert summary["done"] == 3
    assert summary["unprocessed"] == 0

    r = await client.patch(f"/api/v1/social-listening/posts/{ids[1]}", json={"status": "to_reply"})
    assert r.json()["data"].get("repliedAt") is None

    r = await client.delete(f"/api/v1/social-listening/posts/{ids[0]}")
    assert r.status_code == 405


async def test_bulk_refuses_another_sites_query(client, email):
    await prepare(client, email)
    foreign = await add_query(client)

    await prepare(client, f"other-{email}")
    own = await add_query(client)
    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={
            "posts": [
                post_payload("https://a.example/mine", queryId=own),
                post_payload("https://a.example/theirs", queryId=foreign),
            ]
        },
    )
    assert r.status_code == 404
    assert foreign in r.json()["error"]["message"]
    assert "https://a.example/mine" not in await all_posts(client)
