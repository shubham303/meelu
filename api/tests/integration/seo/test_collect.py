import pytest

from tests.integration.seo.test_generators import GUIDE, PRODUCT, prepare
from tests.integration.seo.test_rollup import BASE


def kw(keyword, volume=100, difficulty=20, intent="informational"):
    return {
        "keyword_data": {
            "keyword": keyword,
            "keyword_info": {"search_volume": volume, "cpc": 1.5},
            "keyword_properties": {"keyword_difficulty": difficulty},
            "search_intent_info": {"main_intent": intent},
        }
    }


def ranked(keyword, rank, url, **facts):
    return {
        **kw(keyword, **facts),
        "ranked_serp_element": {
            "serp_item": {"rank_group": rank, "rank_absolute": rank, "url": url, "etv": 12.0}
        },
    }


@pytest.fixture
def vendor(monkeypatch):
    from src.providers.registry import VendorResponse
    from src.providers.seo_data.adapter import SEO_CAPABILITIES, SeoDataAdapter
    from src.providers.seo_data.service import seo_data

    calls = []

    class Fake(SeoDataAdapter):
        id = "fake-seo"
        name = "fake"
        capabilities = SEO_CAPABILITIES
        charges = True

        async def keyword_overview(self, keywords, locale):
            calls.append(("overview", tuple(keywords)))
            return VendorResponse(
                [{"keyword": k, **kw(k)["keyword_data"]} for k in keywords], 30_000
            )

        async def keyword_ideas(self, seeds, locale, limit):
            calls.append(("ideas", tuple(seeds)))
            return VendorResponse(
                [
                    kw(f"{seeds[0]} {suffix}")["keyword_data"] | {"keyword": f"{seeds[0]} {suffix}"}
                    for suffix in ("guide", "tips", "kit")
                ],
                40_000,
            )

        async def ranked_keywords(self, target, locale, limit, filters=None):
            calls.append(("ranked", target))
            if target == "gen.example.com":
                return VendorResponse(
                    [
                        ranked("grinder guide", 4, GUIDE),
                        ranked("buy grinder", 3, PRODUCT, intent="transactional"),
                    ],
                    50_000,
                )
            return VendorResponse(
                [
                    ranked(
                        "burr grinder maintenance", 2, f"https://{target}/maintenance", volume=400
                    ),
                    ranked("grinder dosing cup", 5, f"https://{target}/cup", volume=300),
                    ranked("rival login", 1, f"https://{target}/login", intent="navigational"),
                ],
                50_000,
            )

        async def competitors_domain(self, target, locale, limit):
            calls.append(("rivals", target))
            return VendorResponse(
                [
                    {"domain": "rival-one.com", "intersections": 40, "avg_position": 6.0},
                    {"domain": "rival-two.com", "intersections": 12, "avg_position": 9.0},
                ],
                20_000,
            )

        async def serp_competitors(self, keywords, locale, limit):
            calls.append(("serp_competitors", tuple(keywords)))
            return VendorResponse(
                [
                    {"domain": "rival-one.com", "visibility": 0.8, "keywords_count": 50},
                    {"domain": "gen.example.com", "visibility": 0.5},
                ],
                20_000,
            )

        async def serp_organic(self, keyword, locale, options):
            calls.append(("serp", keyword))
            return VendorResponse(
                {
                    "item_types": ["organic", "people_also_ask"],
                    "items": [
                        {
                            "type": "organic",
                            "rank_group": 1,
                            "rank_absolute": 1,
                            "domain": "rival-one.com",
                            "url": "https://rival-one.com/x",
                            "title": "Rival",
                            "description": "d",
                        },
                        {
                            "type": "organic",
                            "rank_group": 2,
                            "rank_absolute": 2,
                            "domain": "gen.example.com",
                            "url": GUIDE,
                            "title": "Ours",
                        },
                        {"type": "people_also_ask", "items": [{"title": f"What is {keyword}?"}]},
                        {"type": "related_searches", "items": [f"{keyword} near me"]},
                    ],
                },
                25_000,
            )

    monkeypatch.setattr(seo_data, "adapters", [Fake()])
    return calls


async def test_collect_keywords_and_ceiling(client, email, vendor, monkeypatch):
    from src.core import database
    from src.credits.service import credit_service

    async def no_balance_check(db, user_id):
        return None

    async def no_charge(db, user_id, domain, capability, cost, call_id):
        return cost

    monkeypatch.setattr(credit_service, "require_balance", no_balance_check)
    monkeypatch.setattr(credit_service, "charge_vendor_call", no_charge)

    site, _, pages, job = await prepare(client, email)
    r = await client.post(f"{BASE}/collect/keywords", json={"jobId": job["id"], "dryRun": True})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["plan"]["ranked"] is True
    assert vendor == []

    r = await client.post(f"{BASE}/collect/keywords", json={"jobId": job["id"], "maxSeeds": 2})
    body = r.json()["data"]
    assert body["vendorCalls"] == 4, body
    assert body["spentMicros"] == 50_000 + 2 * 40_000 + 30_000
    kinds = [c[0] for c in vendor]
    assert kinds.count("ranked") == 1 and kinds.count("ideas") == 2 and kinds.count("overview") == 1

    keywords = {
        k["keyword"]: k
        for k in (await client.get(f"{BASE}/keywords", params={"page_size": 100})).json()["data"]
    }
    assert keywords["grinder guide"]["ourPosition"] == 4
    assert keywords["grinder guide"]["volume"] == 100
    assert keywords["grinder guide"]["intent"] == "informational"
    assert keywords["grinder guide"]["factsFetchedAt"]
    ideas = [k for k in keywords.values() if k["keyword"].endswith(" kit")]
    assert len(ideas) == 2
    assert all(k["firstSource"] == "ideas" and k["seedKeywordId"] for k in ideas)

    job_row = (await client.get(f"{BASE}/jobs/{job['id']}")).json()["data"]
    assert job_row["vendorMicros"] == body["spentMicros"]

    r = await client.post(f"{BASE}/collect/keywords", json={"jobId": job["id"], "maxSeeds": 2})
    again = r.json()["data"]
    assert again["vendorCalls"] == 0
    assert again["cacheHits"] >= 1

    from sqlalchemy import update

    from src.seo.jobs.model import SeoJob

    async with database.SessionLocal() as db:
        await db.execute(
            update(SeoJob).where(SeoJob.id == job["id"]).values(vendor_ceiling_micros=1)
        )
        await db.commit()
    r = await client.post(
        f"{BASE}/collect/keywords",
        json={"jobId": job["id"], "seeds": ["fresh seed"], "fromRanked": False},
    )
    assert r.status_code == 402, r.text
    assert "ceiling" in r.text


async def test_competitors_gap_and_serps(client, email, vendor, monkeypatch):
    from src.credits.service import credit_service

    async def no_balance_check(db, user_id):
        return None

    async def no_charge(db, user_id, domain, capability, cost, call_id):
        return cost

    monkeypatch.setattr(credit_service, "require_balance", no_balance_check)
    monkeypatch.setattr(credit_service, "charge_vendor_call", no_charge)

    site, _, pages, job = await prepare(client, email)
    r = await client.post(f"{BASE}/collect/competitors", json={"jobId": job["id"]})
    assert r.status_code == 200, r.text
    assert set(r.json()["data"]["competitors"]) == {"rival-one.com", "rival-two.com"}
    competitors = (await client.get(f"{BASE}/competitors")).json()["data"]
    assert all(c["state"] == "candidate" for c in competitors)
    one = next(c for c in competitors if c["domain"] == "rival-one.com")
    assert one["brandTerms"] == ["rival-one"]

    r = await client.post(f"{BASE}/collect/competitor-keywords", json={"jobId": job["id"]})
    assert r.json()["data"]["added"] == 0

    r = await client.patch(
        f"{BASE}/competitors/{one['id']}", json={"state": "confirmed", "brandTerms": ["rival"]}
    )
    assert r.json()["data"]["state"] == "confirmed"
    r = await client.post(f"{BASE}/collect/competitor-keywords", json={"jobId": job["id"]})
    body = r.json()["data"]
    assert body["added"] == 2
    keywords = {
        k["keyword"]: k
        for k in (await client.get(f"{BASE}/keywords", params={"source": "competitor"})).json()[
            "data"
        ]
    }
    assert set(keywords) == {"burr grinder maintenance", "grinder dosing cup"}
    assert keywords["burr grinder maintenance"]["volume"] == 400

    from sqlalchemy import text

    from src.core.database import SessionLocal
    from src.core.ids import uid

    async with SessionLocal() as db:
        ids = {k: keywords[k]["id"] for k in keywords}
        cluster_id = uid("cl")
        await db.execute(
            text(
                "insert into seo_keyword_clusters (id, user_id, site_id, head_keyword_id, size, volume_sum, difficulty_median, created_at, updated_at) "
                "values (:id, (select user_id from seo_keywords where id = :head), :site, :head, 2, 700, 20, now(), now())"
            ),
            {"id": cluster_id, "site": site["id"], "head": ids["burr grinder maintenance"]},
        )
        await db.execute(
            text("update seo_keywords set cluster_id = :c where id = any(cast(:ids as text[]))"),
            {"c": cluster_id, "ids": list(ids.values())},
        )
        await db.commit()

    r = await client.post(
        f"{BASE}/page-suggestions/propose-gaps", json={"jobId": job["id"], "minVolume": 50}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["drafts"] == 1, r.json()
    gap = (
        await client.get(f"{BASE}/page-suggestions", params={"state": "draft", "action": "add"})
    ).json()["data"][0]
    assert gap["topicKey"] == "burr grinder maintenance"
    assert gap["evidence"]["competitors"][0]["domain"] == "rival-one.com"
    assert gap["strategies"] == ["gap"]

    r = await client.post(
        f"{BASE}/collect/serps", json={"jobId": job["id"], "suggestionIds": [gap["id"]]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["refreshed"] == 1
    assert r.json()["data"]["added"] == 2
    paa = (await client.get(f"{BASE}/keywords", params={"source": "serp_paa"})).json()["data"]
    assert paa[0]["keyword"] == "what is burr grinder maintenance?"
    assert paa[0]["seedKeywordId"] == ids["burr grinder maintenance"]

    r = await client.post(
        f"{BASE}/collect/serps", json={"jobId": job["id"], "suggestionIds": [gap["id"]]}
    )
    assert r.json()["data"]["skipped"] == 1

    r = await client.post(
        f"{BASE}/collect/serps", json={"jobId": job["id"], "terms": ["a", "b"], "maxKeywords": 1}
    )
    assert r.status_code == 400

    r = await client.post(
        f"{BASE}/page-suggestions/review-inputs", json={"jobId": job["id"], "prompt": "Gaps"}
    )
    batch = r.json()["data"]
    assert "Gaps" in batch["instructions"]
    assert batch["needsSerp"] == []
    assert len(batch["items"]) == 1
    state = batch["items"][0]["state"]
    assert state["serp"]["results"][0]["domain"] == "rival-one.com"
    assert state["serp"]["results"][1]["ours"] is True
    assert state["questions"] == ["what is burr grinder maintenance?"]

    r = await client.post(
        f"{BASE}/page-suggestions/verdicts",
        json={
            "verdicts": [
                {"id": batch["items"][0]["id"], "verdict": "reviewed", "suggestion": "Brief."}
            ]
        },
    )
    assert r.json()["data"]["reviewed"] == 1


async def test_topic_pages(client, email, vendor, monkeypatch):
    from src.credits.service import credit_service

    async def no_balance_check(db, user_id):
        return None

    async def no_charge(db, user_id, domain, capability, cost, call_id):
        return cost

    monkeypatch.setattr(credit_service, "require_balance", no_balance_check)
    monkeypatch.setattr(credit_service, "charge_vendor_call", no_charge)

    site, _, pages, job = await prepare(client, email)
    r = await client.post(
        f"{BASE}/page-suggestions/propose-topic", json={"jobId": job["id"], "topic": "Cold Brew"}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["collected"]["vendor_calls"] == 2
    assert body["suggestions"]["drafts"] >= 1
    drafts = (
        await client.get(
            f"{BASE}/page-suggestions", params={"state": "draft", "action": "add", "page_size": 50}
        )
    ).json()["data"]
    assert all(d["strategies"] == ["topic"] for d in drafts)
    assert all(d["evidence"]["topic"] == "cold brew" for d in drafts)
