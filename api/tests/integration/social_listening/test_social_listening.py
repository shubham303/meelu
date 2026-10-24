import asyncio
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from tests.conftest import TEST_URL, signup

PG_URL = TEST_URL.replace("postgresql+psycopg://", "postgresql://")


def unit(axis, lean=0.0):
    v = [0.0] * 384
    v[axis] = 1.0
    if lean:
        v[(axis + 1) % 384] = lean
    return "[" + ",".join(repr(x) for x in v) + "]"


def sql(statement, params=()):
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


def set_embedding(table, id, axis, lean=0.0):
    sql(
        f"update {table} set embedding = %s::vector, embed_model = 'test' where id = %s",
        (unit(axis, lean), id),
    )


@pytest.fixture(autouse=True)
def mount_routers():
    from src.app import app
    from src.social_listening.endpoints import router

    prefix = "/api/v1/social-listening"
    mounted = any(str(getattr(r, "path", "")).startswith(prefix) for r in app.routes)
    if not mounted:
        app.include_router(router, prefix="/api/v1")


@pytest.fixture
def vendor(monkeypatch):
    from src.providers.social_search.service import social_search

    calls = []
    replies = {}

    async def search_platform(caller, platform, keywords, since, per_keyword):
        calls.append(
            {"platform": platform, "keywords": keywords, "since": since, "perKeyword": per_keyword}
        )
        reply = replies.get(platform, {"posts": [], "failedKeywords": []})
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(social_search, "search_platform", search_platform)
    sql("delete from social_search_cursor")
    return {"calls": calls, "replies": replies}


async def prepare(client, email, credits=10.0, domain="listen.example.com"):
    await signup(client, email, credits=credits)
    return await add_site(client, domain)


async def add_site(client, domain):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": domain})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    client.headers["x-meelu-site"] = site["id"]
    return site


async def add_line(client, text, keywords):
    r = await client.post("/api/v1/social-listening/queries", json=[{"text": text}])
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/social-listening/queries")
    line = next(q for q in r.json()["data"] if q["text"] == text)
    r = await client.patch(
        f"/api/v1/social-listening/queries/{line['id']}", json={"keywords": keywords}
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


def vendor_post(post_id, text, platform="hackernews", hours_ago=1, title=None):
    return {
        "id": post_id,
        "url": f"https://news.ycombinator.com/item?id={post_id}",
        "platform": platform,
        "author": {"handle": "pg", "displayName": None},
        "title": title,
        "text": text,
        "createdAt": (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat(),
        "engagement": {"score": 3, "comments": 1, "views": None},
        "context": {"subreddit": None, "tags": None},
    }


async def grant(email, usd):
    from sqlalchemy import text

    from src.core.database import unit_of_work
    from src.credits.ledger import credit_ledger_service

    async with unit_of_work() as db:
        user_id = (
            await db.execute(text('SELECT id FROM "user" WHERE email = :e'), {"e": email})
        ).scalar_one()
        await credit_ledger_service.apply(db, user_id, usd * 1_000_000, "grant", "Test credits")


async def start_run(client):
    r = await client.post("/api/v1/social-listening/runs")
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def collect(client, run_id, platform="hackernews"):
    r = await client.post(
        f"/api/v1/social-listening/runs/{run_id}/collect", json={"platform": platform}
    )
    assert r.status_code == 200, r.text
    for _ in range(200):
        r = await client.get(f"/api/v1/social-listening/runs/{run_id}")
        stats = r.json()["data"]["platformStats"].get(platform) or {}
        if stats.get("status") != "running":
            return r.json()["data"]
        await asyncio.sleep(0.02)
    raise AssertionError("collect never finished")


async def posts(client, status=None):
    suffix = f"?status={status}&page_size=100" if status else "?page_size=100"
    r = await client.get(f"/api/v1/social-listening/posts{suffix}")
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def test_config_defaults_and_validation(client, email):
    await prepare(client, email)

    r = await client.get("/api/v1/social-listening/config")
    config = r.json()["data"]
    assert config["platforms"] == []
    for gone in ("maxAgeDays", "resultsPerKeyword", "minRelevance", "strictness", "minSimilarity"):
        assert gone not in config

    r = await client.put(
        "/api/v1/social-listening/config",
        json={"platforms": ["reddit", "facebook", "reddit"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["platforms"] == ["reddit", "facebook"]

    r = await client.put("/api/v1/social-listening/config", json={"platforms": ["youtube"]})
    assert r.status_code == 400

    r = await client.put("/api/v1/social-listening/config", json={"platforms": ["web", "reddit"]})
    assert r.json()["data"]["platforms"] == ["web", "reddit"]


async def test_lines_cap_and_two_keywords(client, email):
    await prepare(client, email)

    r = await client.post(
        "/api/v1/social-listening/queries", json=[{"text": f"line {i}"} for i in range(30)]
    )
    assert r.json()["data"] == {"inserted": 30, "updated": 0}
    r = await client.post("/api/v1/social-listening/queries", json=[{"text": "line 31"}])
    assert r.status_code == 400
    assert "at most 30 lines" in r.json()["error"]["message"]
    r = await client.post(
        "/api/v1/social-listening/queries", json=[{"text": "line 3", "enabled": False}]
    )
    assert r.json()["data"] == {"inserted": 0, "updated": 1}

    r = await client.get("/api/v1/social-listening/queries")
    line = r.json()["data"][0]
    assert "negativeKeywords" not in line
    url = f"/api/v1/social-listening/queries/{line['id']}"
    r = await client.patch(url, json={"keywords": ["only one"]})
    assert r.status_code == 400
    r = await client.patch(url, json={"keywords": ["Slow  Site", "slow site"]})
    assert r.status_code == 400
    r = await client.patch(url, json={"keywords": ["Slow  Site", "wordpress speed"]})
    assert r.json()["data"]["keywords"] == ["slow site", "wordpress speed"]
    r = await client.patch(url, json={"text": "a new wording"})
    assert r.json()["data"]["keywords"] == []


async def test_run_needs_one_dollar_and_one_at_a_time(client, email):
    await prepare(client, email, credits=0.5)
    r = await client.post("/api/v1/social-listening/runs")
    assert r.status_code == 402
    assert r.json()["error"]["message"] == (
        "Social listening needs a credit balance of at least $1."
    )

    await grant(email, 10)
    run = await start_run(client)

    await add_site(client, "second.example.com")
    r = await client.post("/api/v1/social-listening/runs")
    assert r.status_code == 409

    sql(
        "update social_listening_run set updated_at = now() - interval '3 minutes' where id = %s",
        (run["id"],),
    )
    second = await start_run(client)
    assert second["status"] == "running"
    rows = sql("select status, error from social_listening_run where id = %s", (run["id"],))
    assert rows[0][0] == "error"


async def test_estimate_counts_only_keywords_the_vendor_would_be_asked_for(
    client, email, vendor, monkeypatch
):
    from src.providers.social_search.service import social_search

    async def max_cost_micros(platform, keyword_count, per_keyword):
        return keyword_count * per_keyword * 100

    monkeypatch.setattr(social_search, "max_cost_micros", max_cost_micros)
    await prepare(client, email)
    await add_line(client, "people with slow wordpress sites", ["slow wordpress", "site speed"])
    r = await client.post("/api/v1/social-listening/queries", json=[{"text": "new line"}])
    assert r.status_code == 200, r.text
    sql(
        "insert into social_search_cursor (id, platform, keyword, last_fetched_at, "
        "created_at, updated_at) values ('ssc_fresh', 'hackernews', 'site speed', now(), "
        "now(), now())"
    )

    r = await client.get("/api/v1/social-listening/estimate")
    assert r.status_code == 200, r.text
    hackernews = next(p for p in r.json()["data"]["platforms"] if p["platform"] == "hackernews")
    assert hackernews["keywords"] == 4
    assert hackernews["vendorKeywords"] == 3
    assert hackernews["maxCostMicros"] == 3 * 25 * 100
    web = next(p for p in r.json()["data"]["platforms"] if p["platform"] == "web")
    assert web["keywords"] == 2
    assert web["maxCostMicros"] == 2 * 30_000

    site_id = client.headers["x-meelu-site"]
    user_id = sql("select user_id from site where id = %s", (site_id,))[0][0]
    sql(
        "insert into social_listening_cursor (id, user_id, site_id, platform, keyword, "
        "last_fetched_at, created_at, updated_at) values "
        "('slk_web1', %s, %s, 'web', 'new line', now(), now(), now()), "
        "('slk_hn1', %s, %s, 'hackernews', 'slow wordpress', now(), now(), now())",
        (user_id, site_id, user_id, site_id),
    )
    r = await client.get("/api/v1/social-listening/estimate")
    platforms = {p["platform"]: p for p in r.json()["data"]["platforms"]}
    assert platforms["hackernews"]["vendorKeywords"] == 2
    assert platforms["web"]["vendorKeywords"] == 1
    assert platforms["web"]["maxCostMicros"] == 30_000


async def test_collect_combines_vendor_and_shared_posts(client, email, vendor):
    await prepare(client, email)
    await add_line(client, "people with slow wordpress sites", ["slow wordpress", "site speed"])
    await add_line(client, "owners asking about site speed", ["site speed", "page cache"])

    sql(
        "insert into social_post (id, post_key, platform, url, text, posted_at, fetched_at) "
        "values ('sp_shared', 'hackernews:shared', 'hackernews', "
        "'https://news.ycombinator.com/item?id=shared', 'my slow wordpress install', now(), now())"
    )
    sql(
        "insert into social_post (id, post_key, platform, url, text, posted_at, fetched_at) "
        "values ('sp_stale', 'hackernews:stale', 'hackernews', "
        "'https://news.ycombinator.com/item?id=stale', 'slow wordpress again', now(), "
        "now() - interval '9 days')"
    )
    long_text = "Our page cache plugin broke and the whole site crawls along slowly every day now."
    vendor["replies"]["hackernews"] = {
        "posts": [
            vendor_post("1", "anyone fix site speed on shared hosting?"),
            vendor_post("2", long_text),
            vendor_post("3", long_text + " "),
        ],
        "failedKeywords": ["page cache"],
    }

    run = await start_run(client)
    finished = await collect(client, run["id"])
    call = vendor["calls"][0]
    assert sorted(call["keywords"]) == ["page cache", "site speed", "slow wordpress"]
    assert call["perKeyword"] == 25
    since = datetime.fromisoformat(call["since"])
    assert timedelta(days=6, hours=23) < datetime.now(UTC) - since < timedelta(days=7, hours=1)

    stats = finished["platformStats"]["hackernews"]
    assert stats["status"] == "done"
    assert stats["fromVendor"] == 3
    assert stats["fromDatabase"] == 1
    assert stats["candidates"] == 3
    assert stats["failedKeywords"] == ["page cache"]
    assert stats["costMicros"] == 0
    assert finished["fetchedCount"] == 4

    found = await posts(client, "candidate")
    assert {p["postId"] for p in found} >= {"sp_shared"}
    assert "sp_stale" not in {p["postId"] for p in found}

    cursors = dict(
        sql(
            "select keyword, last_fetched_at from social_listening_cursor "
            "where site_id = %s and platform = 'hackernews'",
            (client.headers["x-meelu-site"],),
        )
    )
    assert set(cursors) == {"slow wordpress", "site speed"}

    r = await client.patch(f"/api/v1/social-listening/runs/{run['id']}", json={"status": "done"})
    assert r.json()["data"]["finishedAt"] is not None

    vendor["replies"]["hackernews"] = {
        "posts": [vendor_post("1", "anyone fix site speed on shared hosting?")],
        "failedKeywords": [],
    }
    run = await start_run(client)
    finished = await collect(client, run["id"])
    assert len(await posts(client, "candidate")) == 3
    assert vendor["calls"][1]["keywords"] == ["page cache"]
    skipped = finished["platformStats"]["hackernews"]["skippedQueries"]
    assert sorted(s["query"] for s in skipped) == ["site speed", "slow wordpress"]

    sql(
        "update social_search_cursor set last_fetched_at = now() - interval '13 hours' "
        "where platform = 'hackernews'"
    )
    sql(
        "update social_listening_cursor set last_fetched_at = now() - interval '13 hours' "
        "where platform = 'hackernews'"
    )
    r = await client.patch(f"/api/v1/social-listening/runs/{run['id']}", json={"status": "done"})
    run = await start_run(client)
    await collect(client, run["id"])
    call = vendor["calls"][2]
    assert sorted(call["keywords"]) == ["page cache", "site speed", "slow wordpress"]


async def test_collect_survives_vendor_failure(client, email, vendor):
    from src.providers.errors import ProviderRequestError

    await prepare(client, email)
    await add_line(client, "people with slow sites", ["fail newt", "fail toad"])
    vendor["replies"]["hackernews"] = ProviderRequestError("meelu-public", 502, "down")
    run = await start_run(client)
    finished = await collect(client, run["id"])
    stats = finished["platformStats"]["hackernews"]
    assert stats["status"] == "done"
    assert "down" in stats["error"]
    assert sorted(stats["failedKeywords"]) == ["fail newt", "fail toad"]
    rows = sql(
        "select count(*) from social_listening_cursor where site_id = %s",
        (client.headers["x-meelu-site"],),
    )
    assert rows[0][0] == 0


async def test_gate_then_judge(client, email, vendor):
    await prepare(client, email)
    near = await add_line(client, "people with slow sites", ["gate zebra", "gate yak"])
    far = await add_line(client, "people hiring", ["gate okapi", "gate tapir"])
    vendor["replies"]["hackernews"] = {
        "posts": [
            vendor_post("10", "my site is slow", hours_ago=5),
            vendor_post("11", "who is hiring", hours_ago=1),
            vendor_post("12", "unrelated cooking", hours_ago=2),
            vendor_post("13", "not embedded yet", hours_ago=3),
        ],
        "failedKeywords": [],
    }
    run = await start_run(client)
    await collect(client, run["id"])
    by_url = {p["url"]: p for p in await posts(client, "candidate")}
    post_id = {k.rsplit("=", 1)[1]: v["postId"] for k, v in by_url.items()}

    r = await client.post("/api/v1/social-listening/posts/gate")
    assert r.json()["data"]["pending"] == 6

    set_embedding("social_listening_query", near["id"], 0)
    set_embedding("social_listening_query", far["id"], 5)
    set_embedding("social_post", post_id["10"], 0, lean=0.2)
    set_embedding("social_post", post_id["11"], 5)
    set_embedding("social_post", post_id["12"], 9)
    r = await client.post("/api/v1/social-listening/posts/gate")
    assert r.json()["data"] == {"pending": 1, "matched": 2, "removed": 1}

    matched = {p["url"].rsplit("=", 1)[1]: p for p in await posts(client, "matched")}
    assert set(matched) == {"10", "11"}
    assert matched["10"]["queryId"] == near["id"]
    assert matched["11"]["queryId"] == far["id"]
    assert matched["10"]["similarity"] == pytest.approx(0.98, abs=0.01)

    r = await client.post(
        "/api/v1/social-listening/posts/judged",
        json={
            "posts": [
                {
                    "id": matched["10"]["id"],
                    "keep": True,
                    "keepReason": "Asks for help",
                    "suggestedAngle": "Answer first",
                },
                {"id": matched["11"]["id"], "keep": False},
            ]
        },
    )
    assert r.json()["data"] == {"kept": 1, "removed": 1}
    kept = await posts(client, "to_reply")
    assert [p["keepReason"] for p in kept] == ["Asks for help"]
    assert "relevance" not in kept[0] and "compositeScore" not in kept[0]

    r = await client.patch(
        f"/api/v1/social-listening/posts/{kept[0]['id']}", json={"status": "replied"}
    )
    assert r.json()["data"]["repliedAt"] is not None
    pending = (await posts(client, "candidate"))[0]
    r = await client.patch(
        f"/api/v1/social-listening/posts/{pending['id']}", json={"status": "skipped"}
    )
    assert r.status_code == 409

    r = await client.get("/api/v1/social-listening/summary")
    summary = r.json()["data"]
    assert summary["replied"] == 1
    assert summary["unprocessed"] == 1


async def test_posts_list_newest_first(client, email, vendor):
    await prepare(client, email)
    await add_line(client, "people with slow sites", ["order lynx", "order puma"])
    vendor["replies"]["hackernews"] = {
        "posts": [vendor_post(f"o{i}", f"post {i}", hours_ago=i) for i in (5, 1, 3)],
        "failedKeywords": [],
    }
    run = await start_run(client)
    await collect(client, run["id"])
    assert [p["url"].rsplit("=", 1)[1] for p in await posts(client)] == ["o1", "o3", "o5"]


async def test_purge_drops_old_posts_and_stale_runs(client, email, vendor):
    from src.core.database import unit_of_work
    from src.providers.social_search.store import purge as purge_store
    from src.social_listening.service import social_listening_service

    await prepare(client, email)
    await add_line(client, "people with slow sites", ["purge heron", "purge ibis"])
    vendor["replies"]["hackernews"] = {
        "posts": [vendor_post("old", "old post", hours_ago=24 * 31), vendor_post("new", "new")],
        "failedKeywords": [],
    }
    run = await start_run(client)
    await collect(client, run["id"])
    assert sql("select count(*) from social_post where post_key = 'hackernews:old'")[0][0] == 0
    sql(
        "insert into social_post (id, post_key, platform, url, text, posted_at, fetched_at) "
        "values ('sp_purge_old', 'hackernews:purge_old', 'hackernews', "
        "'https://news.ycombinator.com/item?id=purge_old', 'old post', "
        "now() - interval '31 days', now())"
    )
    sql(
        "update social_listening_run set updated_at = now() - interval '3 hours' where id = %s",
        (run["id"],),
    )

    async with unit_of_work() as db:
        removed = await social_listening_service.purge(db)
    assert removed["runs"] >= 1
    assert (await purge_store())["posts"] >= 1
    assert [p["url"].rsplit("=", 1)[1] for p in await posts(client)] == ["new"]
    r = await client.get(f"/api/v1/social-listening/runs/{run['id']}")
    assert r.json()["data"]["status"] == "error"


async def test_silent_collect_is_closed_and_can_restart(client, email, vendor):
    await prepare(client, email)
    await add_line(client, "people with slow sites", ["beat kudu", "beat gnu"])
    run = await start_run(client)
    sql(
        "update social_listening_run set platform_stats = jsonb_build_object("
        "'hackernews', jsonb_build_object('status', 'running', 'heartbeatAt', "
        "(now() - interval '5 minutes')::text)) where id = %s",
        (run["id"],),
    )
    r = await client.get(f"/api/v1/social-listening/runs/{run['id']}")
    stats = r.json()["data"]["platformStats"]["hackernews"]
    assert stats["status"] == "error"
    assert "stopped reporting" in stats["error"]

    finished = await collect(client, run["id"])
    assert finished["platformStats"]["hackernews"]["status"] == "done"


async def test_collect_beats_while_running(client, email, monkeypatch):
    from src.providers.social_search.service import social_search
    from src.social_listening import collect as collect_module

    monkeypatch.setattr(collect_module, "HEARTBEAT_SECONDS", 0.05)
    release = asyncio.Event()

    async def slow_search(caller, platform, keywords, since, per_keyword):
        await release.wait()
        return {"posts": [], "failedKeywords": []}

    monkeypatch.setattr(social_search, "search_platform", slow_search)
    await prepare(client, email)
    await add_line(client, "people with slow sites", ["beat eland", "beat oryx"])
    run = await start_run(client)
    r = await client.post(
        f"/api/v1/social-listening/runs/{run['id']}/collect", json={"platform": "hackernews"}
    )
    first = r.json()["data"]["platformStats"]["hackernews"]["heartbeatAt"]
    later = first
    for _ in range(100):
        await asyncio.sleep(0.02)
        r = await client.get(f"/api/v1/social-listening/runs/{run['id']}")
        later = r.json()["data"]["platformStats"]["hackernews"].get("heartbeatAt")
        if later != first:
            break
    assert later != first
    release.set()
    finished = await collect(client, run["id"])
    assert finished["platformStats"]["hackernews"]["status"] == "done"


def web_post(url, text, days_ago=1):
    return {
        "url": url,
        "title": f"Thread {url}",
        "text": text,
        "authorName": "Ana",
        "postedAt": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
    }


async def test_web_posts_become_candidates_once(client, email):
    await prepare(client, email)
    await add_line(client, "people with slow sites", ["web zebra", "web yak"])
    run = await start_run(client)
    url = f"/api/v1/social-listening/runs/{run['id']}/web-posts"

    r = await client.post(
        url,
        json={
            "posts": [
                web_post("https://forum.example.org/t/slow-site-help/12", "my site is slow"),
                web_post("https://forum.example.org/t/slow-site-help/12/", "same thread again"),
                web_post("https://forum.example.org/t/old/3", "old thread", days_ago=45),
                web_post("https://q.example.net/questions/9", "speed tips?"),
            ],
            "searchedLines": 1,
            "searchedQueries": ["People with  slow sites"],
        },
    )
    assert r.status_code == 200, r.text
    run = r.json()["data"]
    assert run["platformStats"]["web"] == {
        "status": "done",
        "lines": 1,
        "failedLines": 0,
        "fromVendor": 2,
        "fromDatabase": 0,
        "candidates": 2,
        "skippedQueries": [],
    }
    assert run["fetchedCount"] == 2
    found = await posts(client, "candidate")
    assert {p["platform"] for p in found} == {"web"}
    assert sorted(p["url"] for p in found) == [
        "https://forum.example.org/t/slow-site-help/12",
        "https://q.example.net/questions/9",
    ]

    r = await client.patch(f"/api/v1/social-listening/runs/{run['id']}", json={"status": "done"})
    run = await start_run(client)
    r = await client.post(
        f"/api/v1/social-listening/runs/{run['id']}/web-posts",
        json={
            "posts": [web_post("https://q.example.net/questions/9", "speed tips?")],
            "searchedLines": 1,
            "failedLines": 1,
            "error": "search timed out",
        },
    )
    stats = r.json()["data"]["platformStats"]["web"]
    assert stats["candidates"] == 0
    assert stats["status"] == "error"
    assert stats["error"] == "search timed out"

    r = await client.get("/api/v1/social-listening/searches?platform=web")
    assert [row["query"] for row in r.json()["data"]] == ["people with slow sites"]
    skipped = [{"query": "people with slow sites", "searchedAt": "2026-10-23T05:00:00+00:00"}]
    r = await client.post(
        f"/api/v1/social-listening/runs/{run['id']}/web-posts",
        json={"posts": [], "searchedLines": 0, "skippedQueries": skipped},
    )
    stats = r.json()["data"]["platformStats"]["web"]
    assert (stats["status"], stats["skippedQueries"]) == ("done", skipped)

    r = await client.patch(f"/api/v1/social-listening/runs/{run['id']}", json={"status": "done"})
    r = await client.post(
        f"/api/v1/social-listening/runs/{run['id']}/web-posts", json={"posts": []}
    )
    assert r.status_code == 409


async def test_web_searched_platform_posts_keep_their_platform(client, email):
    await prepare(client, email)
    await add_line(client, "people asking for an seo tool", ["reddit zebra", "reddit yak"])
    run = await start_run(client)
    url = f"/api/v1/social-listening/runs/{run['id']}/web-posts"
    thread = "https://www.reddit.com/r/SaaS/comments/1zx9qa/which_seo_tool_do_you_use/"

    r = await client.post(
        url,
        json={
            "platform": "reddit",
            "posts": [
                {**web_post(thread, "which seo tool do you use?"), "authorHandle": "u/ana_builds"},
                web_post(thread.replace("www.", "old."), "the same thread on old reddit"),
            ],
            "searchedLines": 1,
            "searchedQueries": ["people asking for an seo tool"],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["platformStats"]["reddit"]["candidates"] == 1
    found = await posts(client, "candidate")
    assert [(p["platform"], p["url"]) for p in found] == [("reddit", thread)]
    rows = sql("select post_key, author_handle from social_post where url = %s", (thread,))
    assert rows == [("reddit:1zx9qa", "u/ana_builds")]

    r = await client.get("/api/v1/social-listening/searches?platform=reddit")
    assert [row["query"] for row in r.json()["data"]] == ["people asking for an seo tool"]

    r = await client.post(url, json={"platform": "hackernews", "posts": []})
    assert r.status_code == 400

    r = await client.post(
        f"/api/v1/social-listening/runs/{run['id']}/collect", json={"platform": "reddit"}
    )
    assert r.status_code == 400


async def test_check_keeps_only_posts_that_fit(client, email, vendor, monkeypatch):
    from src.providers.json_data_extractor.service import json_data_extractor

    calls = []

    async def classify(caller, subject, data, questions):
        calls.append((subject, data, questions))
        return {
            "answers": {
                key: {"type": "noul", "noul": 0.2 if "hiring" in q["instructions"] else 0.8}
                for key, q in questions.items()
            }
        }

    monkeypatch.setattr(json_data_extractor, "classify", classify)
    await prepare(client, email)
    line = await add_line(client, "people with slow sites", ["check zebra", "check yak"])
    vendor["replies"]["hackernews"] = {
        "posts": [
            vendor_post("30", "my site is slow"),
            vendor_post("31", "we are hiring"),
        ],
        "failedKeywords": [],
    }
    run = await start_run(client)
    await collect(client, run["id"])
    site_id = client.headers["x-meelu-site"]
    sql(
        "update social_listening_post set status = 'matched', query_id = %s where site_id = %s",
        (line["id"], site_id),
    )
    matched = {p["url"].rsplit("=", 1)[1]: p for p in await posts(client, "matched")}

    r = await client.post(
        "/api/v1/social-listening/posts/check",
        json={"ids": [matched["30"]["id"], matched["31"]["id"]]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"fits": [matched["30"]["id"]], "removed": 1}
    assert calls[0][1] == {"marketer_wrote": "people with slow sites"}
    assert [p["id"] for p in await posts(client, "matched")] == [matched["30"]["id"]]
