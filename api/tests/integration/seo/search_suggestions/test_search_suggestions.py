import pytest

from src.providers.registry import VendorResponse
from src.providers.seo_data.dataforseo import ENDPOINTS, DataForSeoAdapter
from src.providers.seo_data.service import seo_data
from tests.conftest import signup

SERP = {
    "items": [
        {"type": "organic", "rank_group": 1, "url": "https://moz.com/ai", "domain": "moz.com"},
        {
            "type": "people_also_ask",
            "items": [
                {
                    "type": "people_also_ask_element",
                    "title": "Can you use AI to do SEO?",
                    "expanded_element": [
                        {
                            "type": "people_also_ask_expanded_element",
                            "url": "https://moz.com/ai-seo",
                        }
                    ],
                },
                {
                    "type": "people_also_ask_element",
                    "title": "How to rank for AI search?",
                    "expanded_element": [
                        {"type": "people_also_ask_ai_overview_expanded_element", "items": None}
                    ],
                },
                {"type": "people_also_ask_element", "title": "Can you use AI to do SEO?"},
            ],
        },
        {"type": "related_searches", "items": ["SEO for AI Overviews", "Best AI  for SEO"]},
        {"type": "related_searches", "items": ["seo for ai overviews", None]},
    ]
}

AUTOCOMPLETE = {
    "items": [
        {"type": "autocomplete", "suggestion": "seo with ai"},
        {"type": "autocomplete", "suggestion": "SEO with AI tools"},
        {"type": "autocomplete", "suggestion": "seo with ai tools"},
        {"type": "autocomplete", "suggestion": "seo with ai course"},
    ]
}


def envelope(result: dict) -> dict:
    return {
        "status_code": 20000,
        "cost": 0.002,
        "tasks": [{"status_code": 20000, "cost": 0.002, "result": [result]}],
    }


class FakeDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        bodies = {ENDPOINTS["serp"]: SERP, ENDPOINTS["autocomplete"]: AUTOCOMPLETE}
        return VendorResponse(envelope(bodies[query["endpoint"]]), 2_000)


@pytest.fixture
def vendor(monkeypatch):
    fake = FakeDataForSeo()
    monkeypatch.setattr(seo_data, "adapters", [fake])
    return fake


async def test_autocomplete_people_also_ask_and_related_searches(client, email, vendor):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text

    r = await client.post(
        "/api/v1/site/seo/search-suggestions",
        json={"keywords": ["SEO with AI"], "locationCode": 2840},
    )
    assert r.status_code == 200, r.text
    [found] = r.json()["data"]
    assert (found["keyword"], found["locationCode"], found["languageCode"]) == (
        "seo with ai",
        2840,
        "en",
    )
    assert found["autocomplete"] == ["seo with ai tools", "seo with ai course"]
    assert found["peopleAlsoAsk"] == [
        {"question": "Can you use AI to do SEO?", "url": "https://moz.com/ai-seo"},
        {"question": "How to rank for AI search?"},
    ]
    assert found["relatedSearches"] == ["seo for ai overviews", "best ai for seo"]
    assert sorted(q["endpoint"] for q in vendor.sent) == sorted(
        [ENDPOINTS["autocomplete"], ENDPOINTS["serp"]]
    )
    assert vendor.sent[0]["task"] == {
        "keyword": "seo with ai",
        "location_code": 2840,
        "language_code": "en",
    }

    r = await client.post(
        "/api/v1/site/seo/search-suggestions",
        json={"keywords": ["seo with ai"], "locationCode": 2840, "useCache": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == [found]
    assert len(vendor.sent) == 2


async def test_a_blank_keyword_is_rejected(client, email, vendor):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/site/seo/search-suggestions", json={"keywords": ["   "]})
    assert r.status_code == 400
    assert vendor.sent == []


async def test_each_keyword_gets_its_own_suggestions(client, email, vendor):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text

    r = await client.post(
        "/api/v1/site/seo/search-suggestions",
        json={"keywords": ["SEO with AI", "ai seo tools", "seo with ai"], "locationCode": 2840},
    )
    assert r.status_code == 200, r.text
    assert [f["keyword"] for f in r.json()["data"]] == ["seo with ai", "ai seo tools"]
    assert len(vendor.sent) == 4

    r = await client.post(
        "/api/v1/site/seo/search-suggestions",
        json={"keywords": [f"keyword {n}" for n in range(11)]},
    )
    assert r.status_code == 400
