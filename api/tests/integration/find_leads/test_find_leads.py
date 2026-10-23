import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from tests.conftest import TEST_URL, signup

PG_URL = TEST_URL.replace("postgresql+psycopg://", "postgresql://")
BASE = "/api/v1/find-leads"


def sql(statement, params=()):
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


@pytest.fixture(autouse=True)
def mount_routers():
    from src.app import app
    from src.find_leads.endpoints import router

    mounted = any(str(getattr(r, "path", "")).startswith(BASE) for r in app.routes)
    if not mounted:
        app.include_router(router, prefix="/api/v1")


@pytest.fixture
def vendors(monkeypatch):
    from src.providers.people_search.service import people_search
    from src.providers.social_search.service import social_search

    state = {"posts": {}, "people": [], "people_by_page": {}, "activity": {}, "calls": []}

    async def search_platform(caller, platform, keywords, since, per_keyword):
        state["calls"].append(("posts", platform, sorted(keywords)))
        return {"posts": state["posts"].get(platform, []), "failedKeywords": []}

    async def search_linkedin(caller, query, titles, locations, limit, page=1):
        state["calls"].append(("linkedin", query, titles, locations, limit, page))
        return state["people_by_page"].get(page, state["people"])

    async def activity(caller, platform, people, per_person):
        state["calls"].append(("activity", platform, sorted(people)))
        return {p: state["activity"].get(p, []) for p in people}

    monkeypatch.setattr(social_search, "search_platform", search_platform)
    monkeypatch.setattr(people_search, "search_linkedin", search_linkedin)
    monkeypatch.setattr(people_search, "activity", activity)
    monkeypatch.setattr(people_search, "supports", lambda capability: True)
    monkeypatch.setattr(social_search, "supports", lambda capability: True)
    sql("delete from social_search_cursor")
    return state


@pytest.fixture
def decider(monkeypatch):
    from src.providers.json_data_extractor.service import json_data_extractor

    state = {"drop": set(), "fail": False, "calls": []}

    async def classify(caller, subject, data, questions):
        state["calls"].append((subject, data, questions))
        if state["fail"]:
            raise RuntimeError("model down")
        answers = {
            key: {
                "type": "noul",
                "noul": 0.1 if any(h in q["instructions"] for h in state["drop"]) else 0.9,
            }
            for key, q in questions.items()
        }
        return {"answers": answers}

    monkeypatch.setattr(json_data_extractor, "classify", classify)
    return state


RUN_TOKEN = uuid.uuid4().hex[:8]


def vendor_post(post_id, handle, text, platform="reddit", hours_ago=2):
    post_id = f"{post_id}{RUN_TOKEN}"
    return {
        "id": post_id,
        "url": f"https://www.reddit.com/r/shopify/comments/{post_id}/x",
        "platform": platform,
        "author": {"handle": handle, "displayName": None},
        "title": "Traffic dropped",
        "text": text,
        "createdAt": (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat(),
        "engagement": {"score": 3, "comments": 1, "views": None},
        "context": {"subreddit": "shopify", "tags": None},
    }


async def prepare(client, email, credits=10.0, domain="leads.example.com"):
    await signup(client, email, credits=credits)
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": domain})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    client.headers["x-meelu-site"] = site["id"]
    return site


async def add_brief(client, text, sources=None, keywords=None, linkedin=None):
    body = {"text": text} if sources is None else {"text": text, "sources": sources}
    r = await client.post(f"{BASE}/briefs", json=body)
    assert r.status_code == 201, r.text
    brief = r.json()["data"]
    if keywords or linkedin:
        plan = {"keywords": keywords or []}
        if linkedin:
            plan["linkedin"] = linkedin
        r = await client.patch(f"{BASE}/briefs/{brief['id']}", json={"plan": plan})
        assert r.status_code == 200, r.text
        brief = r.json()["data"]
    return brief


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
    r = await client.post(f"{BASE}/runs")
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def wait_for(client, run_id, key):
    for _ in range(300):
        r = await client.get(f"{BASE}/runs/{run_id}")
        stats = r.json()["data"]["sourceStats"].get(key) or {}
        if stats.get("status") not in (None, "running"):
            return r.json()["data"]
        await asyncio.sleep(0.02)
    raise AssertionError(f"{key} never finished")


async def collect(client, run_id, source, platform=None, **extra):
    body = {"source": source} if platform is None else {"source": source, "platform": platform}
    body.update(extra)
    r = await client.post(f"{BASE}/runs/{run_id}/collect", json=body)
    assert r.status_code == 200, r.text
    return await wait_for(client, run_id, f"posts:{platform}" if platform else source)


async def leads(client, status):
    r = await client.get(f"{BASE}/leads?status={status}&page_size=100")
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def test_briefs_crud_limit_and_plan(client, email):
    await prepare(client, email)
    brief = await add_brief(client, "  Shopify   owners whose traffic dropped ")
    assert brief["text"] == "Shopify owners whose traffic dropped"
    assert brief["sources"] == ["posts", "linkedin"]
    assert brief["plan"] == {}

    r = await client.post(f"{BASE}/briefs", json={"text": "Shopify owners whose traffic dropped"})
    assert r.status_code == 409
    r = await client.post(f"{BASE}/briefs", json={"text": "x", "sources": ["tiktok"]})
    assert r.status_code == 400
    r = await client.post(f"{BASE}/briefs", json={"text": "x", "sources": []})
    assert r.status_code == 400

    url = f"{BASE}/briefs/{brief['id']}"
    r = await client.patch(url, json={"plan": {"keywords": ["only one"]}})
    assert r.status_code == 400
    r = await client.patch(
        url,
        json={
            "plan": {
                "keywords": ["Traffic  Dropped", "shopify seo"],
                "linkedin": {"query": "shopify store owner", "titles": ["Owner"]},
                "web": ["shop owners on forums", " shop owners on forums", "a", "b", "c"],
            }
        },
    )
    plan = r.json()["data"]["plan"]
    assert plan["web"] == ["shop owners on forums", "a", "b"]
    assert plan["keywords"] == ["traffic dropped", "shopify seo"]
    assert plan["linkedin"]["query"] == "shopify store owner"

    r = await client.patch(url, json={"sources": ["web"], "enabled": False})
    data = r.json()["data"]
    assert data["sources"] == ["web"] and data["enabled"] is False
    assert data["plan"]["keywords"] == ["traffic dropped", "shopify seo"]
    r = await client.patch(url, json={"text": "a new wording"})
    assert r.json()["data"]["plan"] == {}

    for i in range(9):
        await add_brief(client, f"brief {i}")
    r = await client.post(f"{BASE}/briefs", json={"text": "brief eleven"})
    assert r.status_code == 400
    assert "at most 10 briefs" in r.json()["error"]["message"]

    r = await client.delete(url)
    assert r.json()["data"]["id"] == brief["id"]
    r = await client.get(f"{BASE}/briefs")
    assert len(r.json()["data"]) == 9


async def test_run_guards(client, email):
    await prepare(client, email, credits=1.0)
    r = await client.post(f"{BASE}/runs")
    assert r.status_code == 402
    assert r.json()["error"]["message"] == ("Finding leads needs a credit balance of at least $5.")
    await grant(email, 20)
    r = await client.post(f"{BASE}/runs")
    assert r.status_code == 400
    await add_brief(client, "Shopify owners whose traffic dropped")
    run = await start_run(client)
    r = await client.post(f"{BASE}/runs")
    assert r.status_code == 409
    r = await client.patch(f"{BASE}/runs/{run['id']}", json={"status": "stopped"})
    assert r.json()["data"]["finishedAt"] is not None
    r = await client.post(f"{BASE}/runs/{run['id']}/collect", json={"source": "linkedin"})
    assert r.status_code == 409


async def test_post_authors_become_candidates_once(client, email, vendors):
    await prepare(client, email)
    brief = await add_brief(
        client, "Shopify owners whose traffic dropped", ["posts"], ["walrus dropped", "shop seo"]
    )
    vendors["posts"]["reddit"] = [
        vendor_post("a1", "candlesbydana", "My shop walrus dropped by half after a theme change"),
        vendor_post("a2", "candlesbydana", "Still no idea which pages lost rankings", hours_ago=5),
        vendor_post("b1", "[deleted]", "walrus dropped for me too"),
        vendor_post("c1", "tom_b", "walrus dropped after migrating 400 pages"),
        vendor_post("o1", "old_olga", "walrus dropped back in the day", hours_ago=24 * 40),
    ]
    run = await start_run(client)
    finished = await collect(client, run["id"], "posts", "reddit")
    stats = finished["sourceStats"]["posts:reddit"]
    assert stats["status"] == "done"
    assert stats["candidates"] == 2
    assert finished["foundCount"] == 2

    found = {lead["handle"]: lead for lead in await leads(client, "candidate")}
    assert set(found) == {"candlesbydana", "tom_b"}
    dana = found["candlesbydana"]
    assert dana["profileUrl"] == "https://www.reddit.com/user/candlesbydana/"
    assert dana["briefId"] == brief["id"]
    assert dana["source"] == "posts" and dana["platform"] == "reddit"
    assert len(dana["evidence"]) == 2

    r = await client.patch(f"{BASE}/runs/{run['id']}", json={"status": "done"})
    run = await start_run(client)
    finished = await collect(client, run["id"], "posts", "reddit")
    stats = finished["sourceStats"]["posts:reddit"]
    assert stats["candidates"] == 0
    assert sorted(s["query"] for s in stats["skippedQueries"]) == ["shop seo", "walrus dropped"]
    assert len([c for c in vendors["calls"] if c[0] == "posts"]) == 1
    assert len(await leads(client, "candidate")) == 2


async def test_linkedin_and_web_candidates(client, email, vendors):
    await prepare(client, email)
    brief = await add_brief(
        client,
        "Freelance web designers for local businesses",
        ["linkedin", "web"],
        linkedin={"query": "freelance web designer", "titles": ["Web Designer"]},
    )
    vendors["people"] = [
        {
            "id": "ACwAAA1",
            "name": "Marco Ilic",
            "headline": "Founder at Ilic Studio",
            "profileUrl": "https://www.linkedin.com/in/ACwAAA1",
            "location": "Zagreb",
            "summary": "WordPress sites for restaurants",
        },
        {"id": "nourl", "name": "No Url", "profileUrl": None},
    ]
    run = await start_run(client)
    finished = await collect(client, run["id"], "linkedin")
    assert finished["sourceStats"]["linkedin"]["candidates"] == 1
    assert vendors["calls"][0][1:] == ("freelance web designer", ["Web Designer"], [], 25, 1)

    r = await client.post(
        f"{BASE}/leads/candidates",
        json={
            "runId": run["id"],
            "leads": [
                {
                    "briefId": brief["id"],
                    "name": "Rise Bakery",
                    "website": "https://www.risebakery.example",
                    "profileUrl": "https://www.risebakery.example/about",
                    "email": "Hello@RiseBakery.example",
                    "emailSourceUrl": "https://www.risebakery.example/contact",
                    "snippet": "Bakery blog stopped ranking",
                    "evidence": [{"url": "https://www.risebakery.example/about", "quote": "x"}],
                },
                {
                    "name": "Guessed",
                    "website": "https://guessed.example",
                    "email": "owner@guessed.example",
                },
                {"name": "Nothing to key on"},
            ],
        },
    )
    assert r.json()["data"] == {"inserted": 2, "skipped": 0}
    web = {
        lead["name"]: lead for lead in await leads(client, "candidate") if lead["source"] == "web"
    }
    assert web["Rise Bakery"]["email"] == "hello@risebakery.example"
    assert web["Guessed"].get("email") is None
    run_row = (await client.get(f"{BASE}/runs/{run['id']}")).json()["data"]
    assert run_row["sourceStats"]["web"]["candidates"] == 2
    assert run_row["foundCount"] == 3


async def screen(client, run_id):
    r = await client.post(f"{BASE}/runs/{run_id}/screen")
    assert r.status_code == 200, r.text
    return (await wait_for(client, run_id, "screen"))["sourceStats"]["screen"]


async def test_screen_enrich_judge_and_statuses(client, email, vendors, decider):
    await prepare(client, email)
    await add_brief(client, "Shopify owners", ["posts"], ["otter dropped", "shop seo"])
    vendors["posts"]["reddit"] = [
        vendor_post("f1", "candlesbydana", "My shop otter dropped by half"),
        vendor_post("g1", "agency_bob", "We fix otter dropped issues, DM us"),
        vendor_post("h1", "maybe_mia", "otter dropped, what now"),
    ]
    run = await start_run(client)
    await collect(client, run["id"], "posts", "reddit")
    by_handle = {lead["handle"]: lead for lead in await leads(client, "candidate")}

    decider["drop"] = {"agency_bob"}
    stats = await screen(client, run["id"])
    assert (stats["status"], stats["total"], stats["kept"], stats["removed"]) == ("done", 3, 2, 1)
    subject, data, questions = decider["calls"][0]
    assert data == {"brief": "Shopify owners"}
    assert len(questions) == 3
    assert {lead["handle"] for lead in await leads(client, "shortlisted")} == {
        "candlesbydana",
        "maybe_mia",
    }
    assert sql("select kind from lead_seen where identity_key = 'reddit:agency_bob'") == [
        ("judged",)
    ]

    activity_url = "https://www.reddit.com/r/smallbusiness/comments/z9/x"
    old_url = "https://www.reddit.com/r/smallbusiness/comments/z1/x"
    recent_at = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    old_at = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    vendors["activity"]["candlesbydana"] = [
        {
            "url": activity_url,
            "text": "which pages lost rankings?",
            "at": recent_at,
            "kind": "post",
        },
        {"url": old_url, "text": "2019 rant", "at": old_at, "kind": "post"},
        {"url": "https://x.example/undated", "text": "no date", "at": None, "kind": "comment"},
    ]
    r = await client.post(f"{BASE}/runs/{run['id']}/enrich")
    assert r.status_code == 200, r.text
    finished = await wait_for(client, run["id"], "enrich")
    assert finished["sourceStats"]["enrich"]["people"] == 2
    assert ("activity", "reddit", ["candlesbydana", "maybe_mia"]) in vendors["calls"]
    dana = (await client.get(f"{BASE}/leads/{by_handle['candlesbydana']['id']}")).json()["data"]
    assert dana["enrichedAt"] is not None
    assert activity_url in {a["url"] for a in dana["activity"]}
    assert old_url not in {a["url"] for a in dana["activity"]}
    assert "https://x.example/undated" not in {a["url"] for a in dana["activity"]}

    r = await client.post(
        f"{BASE}/leads/judged",
        json={
            "leads": [
                {
                    "id": dana["id"],
                    "keep": True,
                    "reason": "Traffic halved after a theme change.",
                    "angle": "Offer the list of pages that lost clicks.",
                    "evidence": [
                        {"url": activity_url, "quote": "which pages lost rankings?"},
                        {"url": "https://made.up/url", "quote": "invented"},
                    ],
                },
                {"id": by_handle["maybe_mia"]["id"], "keep": False},
            ]
        },
    )
    assert r.json()["data"] == {"kept": 1, "removed": 1}
    fresh = await leads(client, "new")
    assert [lead["handle"] for lead in fresh] == ["candlesbydana"]
    assert [e["url"] for e in fresh[0]["evidence"]] == [activity_url]
    assert fresh[0]["reason"] == "Traffic halved after a theme change."

    lead_url = f"{BASE}/leads/{dana['id']}"
    r = await client.patch(lead_url, json={"status": "contacted"})
    assert r.json()["data"]["contactedAt"] is not None
    r = await client.patch(lead_url, json={"status": "discarded"})
    data = r.json()["data"]
    assert data["discardedAt"] is not None and data.get("contactedAt") is None
    r = await client.patch(lead_url, json={"status": "candidate"})
    assert r.status_code == 400

    r = await client.get(f"{BASE}/summary")
    summary = r.json()["data"]
    assert (summary["new"], summary["contacted"], summary["discarded"]) == (0, 0, 1)
    assert summary["lastRun"]["id"] == run["id"]

    r = await client.patch(f"{BASE}/runs/{run['id']}", json={"status": "done"})
    vendors["posts"]["reddit"].append(vendor_post("e1", "new_nick", "otter dropped again"))
    sql("delete from social_search_cursor")
    sql("update lead_search set searched_at = now() - interval '13 hours'")
    run = await start_run(client)
    finished = await collect(client, run["id"], "posts", "reddit")
    handles = {lead["handle"] for lead in await leads(client, "candidate")}
    assert handles == {"new_nick"}

    r = await client.delete(lead_url)
    assert r.json()["data"]["id"] == dana["id"]
    assert sql("select kind from lead_seen where identity_key = 'reddit:candlesbydana'") == [
        ("discarded",)
    ]


async def test_purge_forgets_old_rejects_and_drops_old_discards(client, email):
    from src.core.database import unit_of_work
    from src.find_leads.service import find_leads_service

    await prepare(client, email)
    await add_brief(client, "Shopify owners")
    run = await start_run(client)
    site_id = client.headers["x-meelu-site"]
    user_id = sql('select id from "user" where email = %s', (email,))[0][0]
    for key, status, discarded in (
        ("reddit:old_discard", "discarded", "now() - interval '31 days'"),
        ("reddit:recent_discard", "discarded", "now() - interval '2 days'"),
    ):
        sql(
            "insert into lead (id, user_id, site_id, run_id, identity_key, source, platform, "
            f"status, discarded_at) values (%s, %s, %s, %s, %s, 'posts', 'reddit', %s, {discarded})",
            (f"ld_{key[7:]}", user_id, site_id, run["id"], key, status),
        )
    sql(
        "insert into lead_seen (id, user_id, site_id, identity_key, kind, seen_at) values "
        "('ls_old', %s, %s, 'reddit:old_reject', 'judged', now() - interval '31 days')",
        (user_id, site_id),
    )
    sql("update lead_run set updated_at = now() - interval '3 hours' where id = %s", (run["id"],))

    async with unit_of_work() as db:
        removed = await find_leads_service.purge(db)
    assert removed["discarded"] >= 1 and removed["seen"] >= 1 and removed["runs"] >= 1
    keys = {r[0] for r in sql("select identity_key from lead where site_id = %s", (site_id,))}
    assert keys == {"reddit:recent_discard"}
    seen = dict(sql("select identity_key, kind from lead_seen where site_id = %s", (site_id,)))
    assert seen == {"reddit:old_discard": "discarded"}


async def test_runs_take_a_target_and_later_rounds_search_anew(client, email, vendors):
    await prepare(client, email)
    brief = await add_brief(
        client,
        "Agencies",
        ["posts", "linkedin"],
        ["heron agency", "agency seo"],
        linkedin={"query": "marketing agency owner"},
    )
    r = await client.post(f"{BASE}/runs", json={"targetCount": 0})
    assert r.status_code == 400
    r = await client.post(f"{BASE}/runs", json={"targetCount": 101})
    assert r.status_code == 400
    r = await client.post(f"{BASE}/runs", json={"targetCount": 35})
    run = r.json()["data"]
    assert (run["targetCount"], run["round"]) == (35, 0)

    person = lambda i: {"id": f"p{i}", "name": f"P {i}", "profileUrl": f"https://l.in/p{i}"}
    vendors["people_by_page"] = {1: [person(1), person(2)], 2: [person(2), person(3)]}
    finished = await collect(client, run["id"], "linkedin")
    assert finished["sourceStats"]["linkedin"]["candidates"] == 2
    finished = await collect(client, run["id"], "linkedin")
    assert finished["sourceStats"]["linkedin"]["candidates"] == 3
    assert [c[-1] for c in vendors["calls"] if c[0] == "linkedin"] == [1, 2]

    vendors["posts"]["reddit"] = [vendor_post("k1", "kite_kim", "kestrel agency growth")]
    finished = await collect(
        client,
        run["id"],
        "posts",
        "reddit",
        searches=[{"briefId": brief["id"], "keywords": ["kestrel agency", "agency growth"]}],
    )
    assert ("posts", "reddit", ["agency growth", "kestrel agency"]) in vendors["calls"]
    assert finished["sourceStats"]["posts:reddit"]["candidates"] == 1

    r = await client.patch(f"{BASE}/runs/{run['id']}", json={"round": 2})
    assert r.json()["data"]["round"] == 2
    r = await client.patch(f"{BASE}/runs/{run['id']}", json={"round": 11})
    assert r.status_code == 400


async def test_screen_batches_by_hundred_and_reports_failures(client, email, decider):
    await prepare(client, email)
    await add_brief(client, "Shopify owners")
    run = await start_run(client)
    site_id = client.headers["x-meelu-site"]
    user_id = sql('select id from "user" where email = %s', (email,))[0][0]
    for i in range(150):
        sql(
            "insert into lead (id, user_id, site_id, run_id, identity_key, source, platform, name) "
            "values (%s, %s, %s, %s, %s, 'linkedin', 'linkedin', %s)",
            (f"ld_bulk{i}", user_id, site_id, run["id"], f"linkedin:bulk{i}", f"Owner {i}"),
        )
    decider["fail"] = True
    stats = await screen(client, run["id"])
    assert stats["status"] == "error"
    assert stats["error"].startswith("8 of 8 batches failed")
    assert sorted(len(q) for _, _, q in decider["calls"]) == [10] + [20] * 7
    left = sql("select count(*) from lead where site_id = %s and status = 'candidate'", (site_id,))
    assert left == [(150,)]


async def test_starting_a_run_closes_one_the_app_stopped_driving(client, email):
    await prepare(client, email)
    await add_brief(client, "Shopify owners")
    stuck = await start_run(client)
    r = await client.post(f"{BASE}/runs")
    assert r.status_code == 409
    r = await client.patch(f"{BASE}/runs/{stuck['id']}", json={})
    assert r.status_code == 200
    sql(
        "update lead_run set updated_at = now() - interval '3 minutes' where id = %s",
        (stuck["id"],),
    )
    fresh = await start_run(client)
    assert fresh["id"] != stuck["id"]
    old = (await client.get(f"{BASE}/runs/{stuck['id']}")).json()["data"]
    assert old["status"] == "error"
    assert old["finishedAt"] is not None
    assert "stopped working on this run" in old["error"]


async def test_check_drops_misfits_and_web_searches_are_remembered(client, email, vendors, decider):
    await prepare(client, email)
    await add_brief(client, "Shopify owners", ["posts"], ["otter sank", "shop seo"])
    vendors["posts"]["reddit"] = [
        vendor_post("m1", "candlesbydana", "My shop otter sank by half"),
        vendor_post("m2", "agency_bob", "We fix otter sank issues, DM us"),
    ]
    run = await start_run(client)
    await collect(client, run["id"], "posts", "reddit")
    await screen(client, run["id"])
    shortlisted = await leads(client, "shortlisted")
    assert len(shortlisted) == 2

    decider["drop"] = {"agency_bob"}
    r = await client.post(f"{BASE}/leads/check", json={"ids": [x["id"] for x in shortlisted]})
    assert r.status_code == 200, r.text
    out = r.json()["data"]
    dana = next(x for x in shortlisted if x["handle"] == "candlesbydana")
    assert (out["fits"], out["removed"]) == ([dana["id"]], 1)
    assert decider["calls"][-1][0]["task"] == "find_leads_check"
    assert [x["handle"] for x in await leads(client, "shortlisted")] == ["candlesbydana"]

    decider["fail"] = True
    r = await client.post(f"{BASE}/leads/check", json={"ids": [dana["id"]]})
    assert r.status_code == 502

    angle = "Shopify owners on   community forums"
    results = [{"name": "Dana", "website": "https://dana.example", "url": "https://dana.example"}]
    r = await client.put(f"{BASE}/searches/web", json={"query": angle, "results": results})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["query"] == "Shopify owners on community forums"
    r = await client.get(f"{BASE}/searches?platform=web")
    rows = r.json()["data"]
    assert [(row["query"], row["results"]) for row in rows] == [
        ("Shopify owners on community forums", results)
    ]
    r = await client.get(f"{BASE}/searches?platform=reddit")
    assert sorted(row["query"] for row in r.json()["data"]) == ["otter sank", "shop seo"]


async def test_round_keywords_are_saved_on_the_brief(client, email):
    await prepare(client, email)
    brief = await add_brief(client, "Agencies", ["posts"], ["heron agency", "agency seo"])
    plan = {
        "keywords": ["heron agency", "agency seo"],
        "rounds": [{"keywords": ["Heron  Agencies", "agency rankings"], "web": []}],
    }
    r = await client.patch(f"{BASE}/briefs/{brief['id']}", json={"plan": plan})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["plan"]["rounds"] == [
        {"keywords": ["heron agencies", "agency rankings"], "web": []}
    ]
    r = await client.patch(f"{BASE}/briefs/{brief['id']}", json={"text": "Small agencies"})
    assert r.json()["data"]["plan"] == {}
