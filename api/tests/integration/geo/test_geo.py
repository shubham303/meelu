import asyncio
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

from tests.conftest import TEST_URL, signup

PG_URL = TEST_URL.replace("postgresql+psycopg://", "postgresql://")
DOMAIN = "geo.example.com"

STEPS_BODY = "Keyword cannibalization is when pages compete. Steps: open Search Console, filter the query, compare pages."
DEFINITION_BODY = "Keyword cannibalization is when two pages of one site compete for a query."
OTHER_BODY = "Our pricing starts at ten dollars."


def sql(statement, params=()):
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


@pytest.fixture
def llm(monkeypatch):
    from src.geo.prompts import COMPARE, JUDGE_PAGE, UNDERSTAND
    from src.providers.json_data_extractor.adapter import EXTRACT, JsonDataExtractorAdapter
    from src.providers.json_data_extractor.service import json_data_extractor
    from src.providers.registry import VendorResponse

    calls = []

    class FakeExtractor(JsonDataExtractorAdapter):
        id = "fake-extractor"
        name = "Fake extractor"
        capabilities = frozenset({EXTRACT})
        charges = False

        async def extract(self, instructions, data, schema):
            calls.append({"instructions": instructions, "data": data})
            if instructions == UNDERSTAND:
                result = {
                    "intent": "informational",
                    "points": ["what cannibalization is", "steps to find it"],
                }
            elif instructions == JUDGE_PAGE:
                body = data["page"]["body"]
                found = "Steps:" in body
                defined = "cannibalization" in body
                result = {
                    "points": [
                        {
                            "point": "what cannibalization is",
                            "status": "answers" if defined else "missing",
                            "evidence": "when pages compete" if defined else "",
                        },
                        {
                            "point": "steps to find it",
                            "status": "answers" if found else "missing",
                            "evidence": "filter the query" if found else "",
                        },
                    ]
                }
            elif instructions == COMPARE:
                result = {
                    "answers": [
                        {
                            "platform": a["platform"],
                            "covers": ["what cannibalization is"],
                            "misses": ["steps to find it"],
                        }
                        for a in data["answers"]
                    ],
                    "pageAdds": ["Search Console steps"],
                    "suggestion": f"Fake suggestion for {data['verdict']}.",
                }
            else:
                raise AssertionError("unexpected instructions")
            return VendorResponse({"model": "fake-model", "result": result}, 0)

    monkeypatch.setattr(json_data_extractor, "adapters", [FakeExtractor()])
    return calls


@pytest.fixture
def ai(monkeypatch):
    from src.providers.errors import ProviderRequestError
    from src.providers.seo_data.service import seo_data

    state = {"fail": set(), "calls": []}

    async def ai_answer(caller, platform, question, country=None, refresh=False):
        state["calls"].append(platform)
        if platform in state["fail"]:
            raise ProviderRequestError("dataforseo", 502, f"{platform} is down", None)
        cited = f"https://www.{DOMAIN}/blog/cannibalization" if platform == "chat_gpt" else "https://other.example.org/x"
        return {
            "platform": platform,
            "text": f"{platform} says cannibalization is two pages competing.",
            "citations": [{"url": cited, "title": "A source"}],
            "model": "fake",
        }

    async def ai_overview(caller, question, location_code=None, language_code=None, refresh=False):
        state["calls"].append("ai_overview")
        return {"platform": "ai_overview", "shown": False, "text": "", "citations": []}

    monkeypatch.setattr(seo_data, "ai_answer", ai_answer)
    monkeypatch.setattr(seo_data, "ai_overview", ai_overview)
    return state


@pytest.fixture
def search(monkeypatch):
    from src.embed_worker.search.schemas import SearchHit, SearchResult
    from src.embed_worker.search.service import page_search_service

    found = {"pages": []}

    async def search_from_query(db, site_id, query, **kwargs):
        hits = [
            SearchHit(
                page_id=p["id"],
                url=p["url"],
                title=p.get("title"),
                chunk_id=None,
                heading_path=None,
                snippet=None,
                score=1.0 - i / 10,
            )
            for i, p in enumerate(found["pages"])
        ]
        return SearchResult(hits=hits[: kwargs.get("limit", 3)], mode="hybrid", reranked=False)

    monkeypatch.setattr(page_search_service, "search_from_query", search_from_query)
    return found


async def prepare(client, email):
    await signup(client, email, credits=10.0)
    r = await client.post("/api/v1/sites", json={"domain": DOMAIN, "name": "Geo"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    client.headers["x-meelu-site"] = site["id"]
    return site


async def add_page(client, path, body, title=None):
    r = await client.post(
        "/api/v1/site/pages",
        json={"url": f"https://{DOMAIN}{path}", "bodyText": body, "title": title, "contentHash": path},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def add_question(client, text):
    r = await client.post("/api/v1/geo/queries", json=[{"text": text}])
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/geo/queries")
    return next(q for q in r.json()["data"] if q["text"] == text)


async def gsc_position(client, path, position, impressions=100):
    day = (datetime.now(UTC).date() - timedelta(days=3)).isoformat()
    r = await client.post(
        "/api/v1/site/search-data/rows",
        json={
            "days": [
                {
                    "day": day,
                    "rows": [
                        {
                            "query": "keyword cannibalization",
                            "page": f"https://{DOMAIN}{path}/",
                            "device": "DESKTOP",
                            "country": "usa",
                            "clicks": 3,
                            "impressions": impressions,
                            "position": position,
                        }
                    ],
                }
            ]
        },
    )
    assert r.status_code == 200, r.text


async def run_check(client, query_id):
    r = await client.post("/api/v1/geo/checks", json={"queryIds": [query_id]})
    assert r.status_code == 200, r.text
    started = r.json()["data"]["started"]
    assert len(started) == 1
    check_id = started[0]["id"]
    for _ in range(300):
        r = await client.get(f"/api/v1/geo/checks/{check_id}")
        check = r.json()["data"]
        if check["status"] != "running":
            return check
        await asyncio.sleep(0.02)
    raise AssertionError("check never finished")


async def test_questions_are_saved_cleaned_and_edited(client, email):
    await prepare(client, email)

    r = await client.post(
        "/api/v1/geo/queries",
        json=[{"text": "  how do I   find keyword cannibalization "}, {"text": "meelu pricing", "source": "suggested"}],
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 2, "updated": 0}

    r = await client.post("/api/v1/geo/queries", json=[{"text": "meelu pricing", "enabled": False}])
    assert r.json()["data"] == {"inserted": 0, "updated": 1}

    r = await client.get("/api/v1/geo/queries")
    rows = r.json()["data"]
    assert [q["text"] for q in rows] == ["how do I find keyword cannibalization", "meelu pricing"]
    assert rows[1]["enabled"] is False
    assert "latestCheck" not in rows[0]

    r = await client.patch(f"/api/v1/geo/queries/{rows[0]['id']}", json={"text": "meelu pricing"})
    assert r.status_code == 409, r.text
    r = await client.patch(f"/api/v1/geo/queries/{rows[0]['id']}", json={"text": "how to find cannibalization"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["text"] == "how to find cannibalization"

    r = await client.post("/api/v1/geo/queries", json=[{"text": "  "}])
    assert r.status_code == 400
    r = await client.post("/api/v1/geo/queries", json=[{"text": "x", "source": "robot"}])
    assert r.status_code == 400

    r = await client.delete(f"/api/v1/geo/queries/{rows[1]['id']}")
    assert r.status_code == 200, r.text
    r = await client.get(f"/api/v1/geo/queries/{rows[1]['id']}")
    assert r.status_code == 404


async def test_a_full_page_ranked_on_page_one_is_covered(client, email, llm, ai, search):
    await prepare(client, email)
    page = await add_page(client, "/blog/cannibalization", STEPS_BODY, "Cannibalization")
    other = await add_page(client, "/pricing", OTHER_BODY)
    search["pages"] = [other, page]
    await gsc_position(client, "/blog/cannibalization", 4.0)
    question = await add_question(client, "how do I find keyword cannibalization")

    check = await run_check(client, question["id"])

    assert check["status"] == "done", check
    assert check["intent"] == "informational"
    assert check["requiredPoints"] == ["what cannibalization is", "steps to find it"]
    assert check["verdict"] == "covered"
    assert check["pageId"] == page["id"]
    assert check["position"] == 4.0
    assert [p["pageId"] for p in check["pages"]] == [page["id"], other["id"]]
    assert check["pages"][0]["coverage"] == 1.0
    assert check["pages"][1]["coverage"] == 0.0
    assert check["pages"][0]["points"][1]["evidence"] == "filter the query"
    by_platform = {a["platform"]: a for a in check["aiAnswers"]}
    assert by_platform["chat_gpt"]["citedUs"] is True
    assert by_platform["claude"]["citedUs"] is False
    assert by_platform["ai_overview"]["shown"] is False
    assert by_platform["chat_gpt"]["misses"] == ["steps to find it"]
    assert check["pageAdds"] == ["Search Console steps"]
    assert check["suggestion"] == "Fake suggestion for covered."

    judged_bodies = [c["data"]["page"]["body"] for c in llm if "page" in c["data"] and c["data"]["page"] and "points" in c["data"] and "advice" not in c["data"]]
    assert STEPS_BODY in judged_bodies

    r = await client.get("/api/v1/geo/summary")
    summary = r.json()["data"]
    assert summary["covered"] == 1
    assert summary["cited"] == 1
    assert summary["unchecked"] == 0


async def test_a_full_page_without_rank_is_low_rank(client, email, llm, ai, search):
    await prepare(client, email)
    page = await add_page(client, "/blog/cannibalization", STEPS_BODY)
    search["pages"] = [page]
    await gsc_position(client, "/blog/cannibalization", 18.5)
    question = await add_question(client, "how do I find keyword cannibalization")

    check = await run_check(client, question["id"])

    assert check["verdict"] == "low_rank"
    assert check["position"] == 18.5


async def test_a_page_missing_a_point_is_partial(client, email, llm, ai, search):
    await prepare(client, email)
    page = await add_page(client, "/blog/what-is-it", DEFINITION_BODY)
    search["pages"] = [page]
    await gsc_position(client, "/blog/what-is-it", 2.0)
    question = await add_question(client, "how do I find keyword cannibalization")

    check = await run_check(client, question["id"])

    assert check["verdict"] == "partial"
    assert check["pages"][0]["coverage"] == 0.5
    assert check["pages"][0]["points"][1] == {"point": "steps to find it", "status": "missing"}


async def test_no_matching_page_and_a_failed_platform(client, email, llm, ai, search):
    await prepare(client, email)
    search["pages"] = [await add_page(client, "/pricing", OTHER_BODY)]
    ai["fail"] = {"claude"}
    question = await add_question(client, "how do I find keyword cannibalization")

    check = await run_check(client, question["id"])

    assert check["status"] == "done", check
    assert check["verdict"] == "no_page"
    assert "pageId" not in check
    assert check["pageAdds"] == []
    claude = next(a for a in check["aiAnswers"] if a["platform"] == "claude")
    assert claude["shown"] is False
    assert "claude is down" in claude["error"]
    compare = next(c for c in llm if "advice" in c["data"])
    assert compare["data"]["page"] is None
    assert [a["platform"] for a in compare["data"]["answers"]] == ["chat_gpt"]


async def test_check_all_skips_fresh_disabled_and_running(client, email, llm, ai, search):
    await prepare(client, email)
    search["pages"] = []
    fresh = await add_question(client, "first question")
    stale = await add_question(client, "second question")
    off = await add_question(client, "third question")
    await client.patch(f"/api/v1/geo/queries/{off['id']}", json={"enabled": False})
    await run_check(client, fresh["id"])
    await run_check(client, stale["id"])
    sql(
        "update geo_check set started_at = now() - interval '8 days' where query_id = %s",
        (stale["id"],),
    )

    r = await client.post("/api/v1/geo/checks", json={})
    assert r.status_code == 200, r.text
    started = r.json()["data"]["started"]
    assert [c["queryId"] for c in started] == [stale["id"]]

    r = await client.post("/api/v1/geo/checks", json={"queryIds": [stale["id"]]})
    body = r.json()["data"]
    if body["started"]:
        assert body["alreadyRunning"] == 0
    else:
        assert body["alreadyRunning"] == 1

    r = await client.post("/api/v1/geo/checks", json={"queryIds": ["geq_missing"]})
    assert r.status_code == 404


async def test_check_history_and_timed_out_checks(client, email, llm, ai, search):
    await prepare(client, email)
    search["pages"] = []
    question = await add_question(client, "first question")
    done = await run_check(client, question["id"])

    r = await client.get(f"/api/v1/geo/queries/{question['id']}/checks")
    assert [c["id"] for c in r.json()["data"]] == [done["id"]]

    site_id = client.headers["x-meelu-site"]
    user_id = sql("select user_id from geo_query where id = %s", (question["id"],))[0][0]
    sql(
        "insert into geo_check (id, user_id, site_id, query_id, status, started_at) "
        "values ('gec_stuck', %s, %s, %s, 'running', now() - interval '1 hour')",
        (user_id, site_id, question["id"]),
    )
    r = await client.get(f"/api/v1/geo/checks/gec_stuck")
    assert r.json()["data"]["status"] == "error"

    r = await client.delete(f"/api/v1/geo/checks/{done['id']}")
    assert r.status_code == 200, r.text


async def test_stop_ends_running_checks(client, email, monkeypatch):
    from src.geo.check import geo_checker

    await prepare(client, email)
    question = await add_question(client, "first question")
    released = asyncio.Event()

    async def hang(caller, check_id):
        await released.wait()
        return {"verdict": "covered"}

    monkeypatch.setattr(geo_checker, "evaluate", hang)
    r = await client.post("/api/v1/geo/checks", json={"queryIds": [question["id"]]})
    check_id = r.json()["data"]["started"][0]["id"]

    r = await client.post("/api/v1/geo/checks/stop", json={})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["stopped"] == 1
    released.set()
    await asyncio.sleep(0.05)

    r = await client.get(f"/api/v1/geo/checks/{check_id}")
    check = r.json()["data"]
    assert check["status"] == "stopped"
    assert "verdict" not in check

    r = await client.get("/api/v1/geo/summary")
    assert r.json()["data"]["running"] == 0

    r = await client.post("/api/v1/geo/checks/stop", json={})
    assert r.json()["data"]["stopped"] == 0


def test_geo_scopes_always_load_the_seo_desk():
    from src.agent_scope.lib import SiteRef
    from src.agent_scope.registry import AGENT_SCOPES, desk_writes
    from src.agent_scope.service import agent_scope_service

    site = SiteRef(id="site_geo_0001", name="Geo", domain=DOMAIN)
    for action in ("ask-geo", "geo-setup"):
        body = agent_scope_service.scope_response(action, AGENT_SCOPES[action], site).model_dump(
            by_alias=True
        )
        assert body["loadedDesks"] == ["seo"]
        assert desk_writes("seo") <= set(body["writes"])
        assert "seo" not in [d["name"] for d in body["desks"]]
        assert "geo_check" in body["systemPrompt"]
        assert "site_search_daily" in body["systemPrompt"]
        assert body["providers"] == ["seo-data"]

    seo = agent_scope_service.scope_response("ask-seo", AGENT_SCOPES["ask-seo"], site).model_dump(
        by_alias=True
    )
    assert seo["loadedDesks"] == []
    assert "geo" in [d["name"] for d in seo["desks"]]
