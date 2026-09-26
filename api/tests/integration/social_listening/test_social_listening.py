import psycopg
import pytest

from tests.conftest import TEST_URL, signup

PG_URL = TEST_URL.replace("postgresql+psycopg://", "postgresql://")


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


async def classify(client, post_id, status="needs_reply", **fields):
    r = await client.post(
        "/api/v1/social-listening/posts/classified",
        json={"posts": [{"id": post_id, "status": status, **fields}]},
    )
    assert r.status_code == 200, r.text


async def posts_by_url(client):
    r = await client.get("/api/v1/social-listening/posts")
    assert r.status_code == 200, r.text
    return {p["url"]: p for p in r.json()["data"]}


def post_payload(url, **extra):
    base = {
        "url": url,
        "platform": "reddit",
        "kind": "topic",
        "title": "How do I automate SEO audits?",
        "text": "Looking for a tool that watches my rankings.",
        "engagement": {"score": 42, "comments": 10},
        "context": {"subreddit": "seo"},
        "matchedTargets": [],
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
    assert config["minRelevance"] == pytest.approx(0.6)
    assert config["maxAgeDays"] == 365
    assert config["dropDeadPosts"] is True
    assert config["minSimilarity"] == pytest.approx(0.8)
    assert config.get("schedule") is None

    r = await client.put(
        "/api/v1/social-listening/config",
        json={
            "minSimilarity": 0.7,
            "platforms": ["reddit", "hackernews"],
            "resultsPerKeyword": 25,
            "schedule": "weekly",
            "dropDeadPosts": False,
        },
    )
    assert r.status_code == 200, r.text
    updated = r.json()["data"]
    assert updated["id"] == config["id"]
    assert updated["minSimilarity"] == pytest.approx(0.7)
    assert updated["platforms"] == ["reddit", "hackernews"]
    assert updated["resultsPerKeyword"] == 25
    assert updated["schedule"] == "weekly"
    assert updated["dropDeadPosts"] is False
    assert updated["maxAgeDays"] == 365

    r = await client.get("/api/v1/social-listening/config")
    assert r.json()["data"]["minSimilarity"] == pytest.approx(0.7)


async def test_queries_upsert_patch_delete(client, email):
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
            {"text": "anyone comparing backlink checkers"},
        ],
    )
    assert r.json()["data"] == {"inserted": 1, "updated": 1}

    r = await client.get("/api/v1/social-listening/queries")
    assert r.status_code == 200, r.text
    queries = r.json()["data"]
    assert [q["text"] for q in queries] == [
        "people asking which tool tracks rankings",
        "someone frustrated their audit missed issues",
        "anyone comparing backlink checkers",
    ]
    first = queries[0]
    assert first["enabled"] is False
    assert first["source"] == "user"
    assert first["keywords"] == []
    assert first["embedded"] is False
    assert queries[1]["source"] == "suggested"

    r = await client.patch(
        f"/api/v1/social-listening/queries/{first['id']}",
        json={
            "enabled": True,
            "keywords": ["rank tracker", "serp tracking"],
            "negativeKeywords": ["job"],
        },
    )
    assert r.status_code == 200, r.text
    patched = r.json()["data"]
    assert patched["enabled"] is True
    assert patched["keywords"] == ["rank tracker", "serp tracking"]
    assert patched["negativeKeywords"] == ["job"]

    set_embedding("social_listening_query", first["id"], 0)
    r = await client.get("/api/v1/social-listening/queries")
    assert r.json()["data"][0]["embedded"] is True

    r = await client.patch(
        f"/api/v1/social-listening/queries/{first['id']}",
        json={"text": "people asking about rank tracking"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["embedded"] is False
    assert r.json()["data"]["keywords"] == []

    r = await client.patch(f"/api/v1/social-listening/queries/{first['id']}", json={"text": "  "})
    assert r.status_code == 400

    r = await client.delete(f"/api/v1/social-listening/queries/{first['id']}")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["id"] == first["id"]

    r = await client.get("/api/v1/social-listening/queries")
    assert len(r.json()["data"]) == 2

    r = await client.patch(
        f"/api/v1/social-listening/queries/{first['id']}", json={"enabled": True}
    )
    assert r.status_code == 404


async def test_targets_upsert_patch_delete(client, email):
    await prepare(client, email)

    r = await client.post(
        "/api/v1/social-listening/targets",
        json=[
            {"kind": "brand", "name": "Meelu", "source": "profile"},
            {"kind": "competitor", "name": "Ahrefs"},
            {"kind": "competitor", "name": "Semrush", "source": "suggested"},
        ],
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 3, "updated": 0}

    r = await client.post(
        "/api/v1/social-listening/targets",
        json=[{"kind": "competitor", "name": "Ahrefs", "enabled": False}],
    )
    assert r.json()["data"] == {"inserted": 0, "updated": 1}

    r = await client.post(
        "/api/v1/social-listening/targets", json=[{"kind": "vendor", "name": "X"}]
    )
    assert r.status_code == 400

    r = await client.get("/api/v1/social-listening/targets")
    targets = r.json()["data"]
    assert len(targets) == 3
    ahrefs = next(t for t in targets if t["name"] == "Ahrefs")
    assert ahrefs["enabled"] is False
    assert ahrefs["kind"] == "competitor"

    r = await client.patch(
        f"/api/v1/social-listening/targets/{ahrefs['id']}", json={"enabled": True}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["enabled"] is True

    r = await client.delete(f"/api/v1/social-listening/targets/{ahrefs['id']}")
    assert r.status_code == 200
    r = await client.get("/api/v1/social-listening/targets")
    assert len(r.json()["data"]) == 2


async def test_runs_lifecycle_and_list(client, email):
    await prepare(client, email)

    r = await client.post("/api/v1/social-listening/runs")
    assert r.status_code == 201, r.text
    run = r.json()["data"]
    assert run["status"] == "running"
    assert run["startedAt"] is not None
    assert run.get("finishedAt") is None
    assert run["fetchedCount"] == 0
    assert run["platformStats"] == {}

    r = await client.patch(
        f"/api/v1/social-listening/runs/{run['id']}",
        json={
            "status": "done",
            "fetchedCount": 120,
            "keptCount": 14,
            "platformStats": {"reddit": {"fetched": 120, "kept": 14}},
        },
    )
    assert r.status_code == 200, r.text
    done = r.json()["data"]
    assert done["status"] == "done"
    assert done["finishedAt"] is not None
    assert done["fetchedCount"] == 120
    assert done["keptCount"] == 14
    assert done["platformStats"]["reddit"]["kept"] == 14

    r = await client.patch(f"/api/v1/social-listening/runs/{run['id']}", json={"status": "flying"})
    assert r.status_code == 400

    r = await client.post("/api/v1/social-listening/runs")
    second = r.json()["data"]

    r = await client.get("/api/v1/social-listening/runs")
    assert r.status_code == 200, r.text
    body = r.json()
    assert [x["id"] for x in body["data"]] == [second["id"], run["id"]]
    assert body["pagination"]["total"] == 2

    r = await client.get(f"/api/v1/social-listening/runs/{run['id']}")
    assert r.json()["data"]["status"] == "done"


async def test_posts_bulk_insert_skips_known_urls(client, email):
    await prepare(client, email)
    r = await client.post("/api/v1/social-listening/runs")
    run_id = r.json()["data"]["id"]

    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={
            "runId": run_id,
            "posts": [
                post_payload("https://reddit.com/r/seo/1"),
                post_payload("https://reddit.com/r/seo/2", kind="brand", matchedTargets=["Meelu"]),
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 2, "updated": 0}

    r = await client.get("/api/v1/social-listening/posts")
    posts = r.json()["data"]
    assert len(posts) == 2

    r = await client.post(
        "/api/v1/social-listening/posts/known",
        json={
            "urls": [
                "https://reddit.com/r/seo/1",
                "https://reddit.com/r/seo/2",
                "https://reddit.com/r/seo/new",
                " https://reddit.com/r/seo/1 ",
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert sorted(r.json()["data"]) == [
        "https://reddit.com/r/seo/1",
        "https://reddit.com/r/seo/2",
    ]
    first = next(p for p in posts if p["url"] == "https://reddit.com/r/seo/1")
    assert first["status"] == "fetched"
    assert first["runId"] == run_id
    assert first["engagement"]["score"] == 42
    assert first.get("similarity") is None

    r = await client.patch(
        f"/api/v1/social-listening/posts/{first['id']}", json={"status": "drafted"}
    )
    assert r.status_code == 200

    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={"posts": [post_payload("https://reddit.com/r/seo/1", engagement={"score": 90})]},
    )
    assert r.json()["data"] == {"inserted": 0, "updated": 1}

    r = await client.get("/api/v1/social-listening/posts")
    posts = r.json()["data"]
    assert len(posts) == 2
    same = next(p for p in posts if p["url"] == "https://reddit.com/r/seo/1")
    assert same["id"] == first["id"]
    assert same["engagement"] == {"score": 42, "comments": 10}
    assert same["status"] == "drafted"

    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={"runId": "slr_missing", "posts": [post_payload("https://x.com/1")]},
    )
    assert r.status_code == 404


async def test_gate_and_classify_are_incremental(client, email):
    await prepare(client, email)
    r = await client.post(
        "/api/v1/social-listening/queries", json=[{"text": "people asking about rank tracking"}]
    )
    r = await client.get("/api/v1/social-listening/queries")
    query_id = r.json()["data"][0]["id"]

    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={
            "posts": [
                post_payload("https://a/close", queryId=query_id),
                post_payload("https://a/far", queryId=query_id),
                post_payload("https://a/later", queryId=query_id),
                post_payload("https://a/brand", kind="brand", matchedTargets=["Meelu"]),
                post_payload(
                    "https://a/noise",
                    queryId=query_id,
                    status="filtered",
                    keepReason="negative keyword",
                ),
            ]
        },
    )
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/social-listening/posts")
    by_url = {p["url"]: p for p in r.json()["data"]}

    r = await client.post("/api/v1/social-listening/posts/gate")
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"pending": 3, "scored": 0, "kept": 0, "filtered": 0}
    r = await client.get("/api/v1/social-listening/posts?status=matched")
    assert [p["url"] for p in r.json()["data"]] == ["https://a/brand"]

    set_embedding("social_listening_query", query_id, 0)
    set_embedding("social_listening_post", by_url["https://a/close"]["id"], 0)
    set_embedding("social_listening_post", by_url["https://a/far"]["id"], 1)

    r = await client.post("/api/v1/social-listening/posts/gate")
    assert r.json()["data"] == {"pending": 1, "scored": 2, "kept": 1, "filtered": 1}

    r = await client.get("/api/v1/social-listening/posts?status=matched&sort=similarity")
    matched = r.json()["data"]
    assert [p["url"] for p in matched] == ["https://a/close", "https://a/brand"]
    assert matched[0]["similarity"] == pytest.approx(1.0)
    r = await client.get("/api/v1/social-listening/posts?status=filtered")
    filtered = {p["url"]: p for p in r.json()["data"]}
    assert filtered["https://a/far"]["keepReason"] == "Too far from the query"
    assert filtered["https://a/noise"]["keepReason"] == "negative keyword"
    r = await client.get("/api/v1/social-listening/posts?status=fetched")
    assert [p["url"] for p in r.json()["data"]] == ["https://a/later"]

    r = await client.post(
        "/api/v1/social-listening/posts/classified",
        json={
            "posts": [
                {
                    "id": by_url["https://a/close"]["id"],
                    "status": "needs_reply",
                    "intent": "seeking_tool",
                    "sentiment": "neutral",
                    "isQuestion": True,
                    "classes": ["question"],
                    "relevance": 0.9,
                    "compositeScore": 0.8,
                    "keepReason": "asks for a tracker",
                }
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 0, "updated": 1}
    r = await client.get(f"/api/v1/social-listening/posts/{by_url['https://a/close']['id']}")
    close = r.json()["data"]
    assert close["status"] == "needs_reply"
    assert close["intent"] == "seeking_tool"
    assert close["similarity"] == pytest.approx(1.0)
    assert close["queryId"] == query_id

    r = await client.get("/api/v1/social-listening/posts?status=matched")
    assert [p["url"] for p in r.json()["data"]] == ["https://a/brand"]

    r = await client.post(
        "/api/v1/social-listening/posts/classified",
        json={"posts": [{"id": by_url["https://a/brand"]["id"], "status": "drafted"}]},
    )
    assert r.status_code == 400
    r = await client.post(
        "/api/v1/social-listening/posts/classified",
        json={"posts": [{"id": "slp_missing", "status": "filtered"}]},
    )
    assert r.status_code == 404

    r = await client.get("/api/v1/social-listening/summary")
    summary = r.json()["data"]
    assert summary["unprocessed"] == 2
    assert summary["needsReply"] == 1
    assert summary["keptByQuery"] == [
        {"id": query_id, "text": "people asking about rank tracking", "kept": 1}
    ]


async def test_post_filters_sort_and_reply(client, email):
    await prepare(client, email)
    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={
            "posts": [
                post_payload("https://reddit.com/p/topic", engagement={"score": 5}),
                post_payload(
                    "https://reddit.com/p/brand",
                    kind="brand",
                    platform="x",
                    matchedTargets=["Meelu"],
                    engagement={"score": 100},
                    title="Meelu is great",
                ),
                post_payload(
                    "https://reddit.com/p/competitor",
                    kind="competitor",
                    matchedTargets=["Ahrefs"],
                    engagement={"score": 50},
                    title="Ahrefs pricing is painful",
                ),
            ]
        },
    )
    assert r.status_code == 200, r.text
    by_url = await posts_by_url(client)
    await classify(
        client,
        by_url["https://reddit.com/p/topic"]["id"],
        intent="seeking_tool",
        compositeScore=0.9,
        relevance=0.9,
    )
    await classify(
        client,
        by_url["https://reddit.com/p/brand"]["id"],
        intent="praising",
        sentiment="positive",
        classes=["praise"],
        compositeScore=0.5,
        relevance=0.4,
    )
    await classify(
        client,
        by_url["https://reddit.com/p/competitor"]["id"],
        intent="complaining",
        sentiment="negative",
        classes=["complaint", "switch_opportunity"],
        compositeScore=0.7,
        relevance=0.6,
    )

    r = await client.get("/api/v1/social-listening/posts", params={"kind": "brand"})
    assert [p["url"] for p in r.json()["data"]] == ["https://reddit.com/p/brand"]

    r = await client.get("/api/v1/social-listening/posts", params={"cls": "switch_opportunity"})
    assert [p["url"] for p in r.json()["data"]] == ["https://reddit.com/p/competitor"]

    r = await client.get("/api/v1/social-listening/posts", params={"minRelevance": 0.5})
    assert {p["url"] for p in r.json()["data"]} == {
        "https://reddit.com/p/topic",
        "https://reddit.com/p/competitor",
    }

    r = await client.get("/api/v1/social-listening/posts", params={"target": "Ahrefs"})
    assert [p["url"] for p in r.json()["data"]] == ["https://reddit.com/p/competitor"]

    r = await client.get("/api/v1/social-listening/posts", params={"q": "pricing"})
    assert [p["url"] for p in r.json()["data"]] == ["https://reddit.com/p/competitor"]

    r = await client.get("/api/v1/social-listening/posts", params={"sort": "best"})
    assert [p["compositeScore"] for p in r.json()["data"]] == pytest.approx([0.9, 0.7, 0.5])

    r = await client.get("/api/v1/social-listening/posts", params={"sort": "engaged"})
    assert [p["engagement"]["score"] for p in r.json()["data"]] == [100, 50, 5]

    r = await client.get("/api/v1/social-listening/posts", params={"sort": "worst"})
    assert r.status_code == 400

    r = await client.get("/api/v1/social-listening/posts", params={"status": "needs_reply"})
    brand = next(p for p in r.json()["data"] if p["kind"] == "brand")
    assert brand.get("repliedAt") is None

    r = await client.patch(
        f"/api/v1/social-listening/posts/{brand['id']}",
        json={"status": "replied", "replyText": "Thanks for the kind words!"},
    )
    assert r.status_code == 200, r.text
    replied = r.json()["data"]
    assert replied["status"] == "replied"
    assert replied["replyText"] == "Thanks for the kind words!"
    assert replied["repliedAt"] is not None

    r = await client.get(f"/api/v1/social-listening/posts/{brand['id']}")
    assert r.json()["data"]["repliedAt"] is not None

    r = await client.delete(f"/api/v1/social-listening/posts/{brand['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/social-listening/posts/{brand['id']}")
    assert r.status_code == 404


async def test_summary_counts(client, email):
    await prepare(client, email)
    r = await client.post("/api/v1/social-listening/queries", json=[{"text": "rank tracking"}])
    r = await client.get("/api/v1/social-listening/queries")
    query_id = r.json()["data"][0]["id"]
    r = await client.post("/api/v1/social-listening/runs")
    run_id = r.json()["data"]["id"]
    r = await client.patch(
        f"/api/v1/social-listening/runs/{run_id}",
        json={"status": "done", "fetchedCount": 10, "keptCount": 4},
    )
    assert r.status_code == 200

    r = await client.post(
        "/api/v1/social-listening/posts/bulk",
        json={
            "runId": run_id,
            "posts": [
                post_payload("https://a/1", queryId=query_id),
                post_payload("https://a/2", kind="brand"),
                post_payload("https://a/3", kind="brand"),
                post_payload("https://a/4", kind="competitor"),
                post_payload("https://a/5", queryId=query_id),
            ],
        },
    )
    assert r.status_code == 200, r.text
    posts = await posts_by_url(client)
    await classify(client, posts["https://a/1"]["id"], sentiment="neutral", classes=["question"])
    await classify(client, posts["https://a/2"]["id"], sentiment="positive", classes=["praise"])
    await classify(
        client,
        posts["https://a/3"]["id"],
        sentiment="negative",
        classes=["complaint", "feature_request"],
    )
    await classify(
        client, posts["https://a/4"]["id"], sentiment="negative", classes=["switch_opportunity"]
    )
    await client.patch(
        f"/api/v1/social-listening/posts/{posts['https://a/2']['id']}",
        json={"status": "replied"},
    )
    await client.patch(
        f"/api/v1/social-listening/posts/{posts['https://a/3']['id']}",
        json={"status": "drafted"},
    )
    await client.patch(
        f"/api/v1/social-listening/posts/{posts['https://a/4']['id']}",
        json={"status": "skipped"},
    )

    r = await client.get("/api/v1/social-listening/summary")
    assert r.status_code == 200, r.text
    summary = r.json()["data"]
    assert summary["unprocessed"] == 1
    assert summary["needsReply"] == 1
    assert summary["drafted"] == 1
    assert summary["replied"] == 1
    assert summary["skipped"] == 1
    assert summary["brandMentions"] == 2
    assert summary["competitorMentions"] == 1
    assert summary["lastRun"]["id"] == run_id
    assert summary["lastRun"]["status"] == "done"
    assert summary["keptByQuery"] == [{"id": query_id, "text": "rank tracking", "kept": 1}]
    assert summary["mentionClasses"] == {
        "praise": 1,
        "complaint": 1,
        "featureRequest": 1,
        "question": 1,
        "switchOpportunity": 1,
    }
    assert summary["sentiment"] == {"positive": 1, "neutral": 1, "negative": 2}
