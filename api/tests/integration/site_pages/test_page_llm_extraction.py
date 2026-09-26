import pytest

from src.providers.errors import ProviderRequestError
from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import VendorResponse
from src.site_pages.llm_extraction.classify import site_page_classifier
from tests.conftest import signup


class FakeJev(JsonDataExtractorAdapter):
    id = "fake-jev"
    name = "Fake Jev"
    capabilities = frozenset({DECIDE})

    def __init__(self):
        self.calls = []

    async def decide(self, state, questions):
        self.calls.append(state)
        if "boom" in state["url"]:
            raise ProviderRequestError(self.id, 502, "jev down")
        page_type = "company" if "about" in state["url"] else "money"
        return VendorResponse(
            {
                "model": "~typesafe/jev-latest",
                "answers": {
                    "page_type": {
                        "type": "choice",
                        "choice": page_type,
                        "probabilities": {page_type: 0.9},
                        "confidence": 0.9,
                    }
                },
            },
            42,
        )


@pytest.fixture
def jev(monkeypatch):
    fake = FakeJev()
    monkeypatch.setattr(json_data_extractor, "adapters", [fake])
    return fake


@pytest.fixture
async def site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "extract.example.com", "name": "X"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def add_page(client, url, **fields):
    r = await client.post("/api/v1/site/pages", json={"url": url, **fields})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_pass_classifies_pending_pages(client, site, jev):
    a = await add_page(
        client,
        "https://extract.example.com/about",
        bodyText="About us",
        metaDescription="Who we are",
        contentHash="h1",
    )
    b = await add_page(
        client, "https://extract.example.com/pricing", bodyText="Pricing", contentHash="h2"
    )
    broken = await add_page(
        client, "https://extract.example.com/boom", bodyText="Broken", contentHash="h3"
    )
    await add_page(client, "https://extract.example.com/empty", contentHash="h4")

    r = await client.get("/api/v1/site/page-llm-extractions/stats")
    assert r.json()["data"]["stats"] == {"eligible": 3, "extracted": 0, "pending": 3}

    assert await site_page_classifier.run_extraction_pass(site["id"]) == 3

    assert len(jev.calls) == 3
    assert "Who we are" in [c["meta_description"] for c in jev.calls]

    r = await client.get(f"/api/v1/site/page-llm-extractions/by-page/{a['id']}")
    assert r.json()["data"]["pageType"] == "company"
    assert r.json()["data"]["confidence"] == 0.9
    assert r.json()["data"]["model"] == "~typesafe/jev-latest"
    assert r.json()["data"]["extractedFromHash"] == "h1"

    r = await client.get(f"/api/v1/site/page-llm-extractions/by-page/{b['id']}")
    assert r.json()["data"]["pageType"] == "money"

    r = await client.get(f"/api/v1/site/page-llm-extractions/by-page/{broken['id']}")
    assert r.json()["data"].get("pageType") is None
    assert "jev down" in r.json()["data"]["error"]

    r = await client.get("/api/v1/site/page-llm-extractions/stats")
    assert r.json()["data"]["stats"]["extracted"] == 2
    assert r.json()["data"]["stats"]["pending"] == 1

    r = await client.get("/api/v1/site/page-llm-extractions?page_type=money")
    assert [x["pageId"] for x in r.json()["data"]] == [b["id"]]

    assert await site_page_classifier.run_extraction_pass(site["id"]) == 1
    assert len(jev.calls) == 4
    assert await site_page_classifier.run_extraction_pass(site["id"]) == 1
    assert await site_page_classifier.run_extraction_pass(site["id"]) == 0
    assert len(jev.calls) == 5

    r = await client.get("/api/v1/providers/calls?domain=json-data-extractor")
    assert r.status_code == 200, r.text
    calls = r.json()["data"]
    assert len(calls) == 5
    assert {c["status"] for c in calls} == {"ok", "error"}

    r = await client.patch(f"/api/v1/site/pages/{a['id']}", json={"contentHash": "h1-new"})
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/site/page-llm-extractions/stats")
    assert r.json()["data"]["stats"]["pending"] == 1

    assert await site_page_classifier.run_extraction_pass(site["id"]) == 1
    r = await client.get(f"/api/v1/site/page-llm-extractions/by-page/{a['id']}")
    assert r.json()["data"]["extractedFromHash"] == "h1-new"


async def test_pass_with_nothing_pending_does_nothing(client, site, jev):
    assert await site_page_classifier.run_extraction_pass(site["id"]) == 0
    assert jev.calls == []


async def test_manual_save_and_delete(client, site):
    a = await add_page(client, "https://extract.example.com/a", bodyText="x", contentHash="h1")
    r = await client.post(
        "/api/v1/site/page-llm-extractions",
        json={"pageId": a["id"], "pageType": "hub", "confidence": 0.5, "extractedFromHash": "h1"},
    )
    assert r.status_code == 201, r.text
    saved = r.json()["data"]
    assert saved["pageType"] == "hub"

    r = await client.post(
        "/api/v1/site/page-llm-extractions", json={"pageId": "pg_missing", "pageType": "hub"}
    )
    assert r.status_code == 404
    r = await client.post(
        "/api/v1/site/page-llm-extractions", json={"pageId": a["id"], "pageType": "nonsense"}
    )
    assert r.status_code == 400

    r = await client.delete(f"/api/v1/site/page-llm-extractions/{saved['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/site/page-llm-extractions/{saved['id']}")
    assert r.status_code == 404


class UnsureJev(FakeJev):
    async def decide(self, state, questions):
        self.calls.append(state)
        return VendorResponse(
            {
                "model": "~typesafe/jev-latest",
                "answers": {
                    "page_type": {
                        "type": "choice",
                        "choice": "money",
                        "probabilities": {"money": 0.4},
                        "confidence": 0.4,
                    }
                },
            },
            42,
        )


@pytest.fixture
def unsure_jev(monkeypatch):
    fake = UnsureJev()
    monkeypatch.setattr(json_data_extractor, "adapters", [fake])
    return fake


async def test_low_confidence_leaves_the_type_unset_and_is_not_retried(client, site, unsure_jev):
    a = await add_page(client, "https://extract.example.com/unsure", bodyText="x", contentHash="h1")

    assert await site_page_classifier.run_extraction_pass(site["id"]) == 1

    r = await client.get(f"/api/v1/site/page-llm-extractions/by-page/{a['id']}")
    assert r.json()["data"].get("pageType") is None
    assert r.json()["data"]["confidence"] == 0.4
    assert r.json()["data"].get("error") is None

    assert await site_page_classifier.run_extraction_pass(site["id"]) == 0
    assert len(unsure_jev.calls) == 1


async def test_set_page_type_fills_an_unset_type_only(client, site, unsure_jev):
    a = await add_page(client, "https://extract.example.com/unsure", bodyText="x", contentHash="h1")
    assert await site_page_classifier.run_extraction_pass(site["id"]) == 1

    r = await client.post(
        f"/api/v1/site/page-llm-extractions/by-page/{a['id']}/page-type",
        json={"pageType": "hub"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["pageType"] == "hub"
    assert r.json()["data"]["extractedFromHash"] == "h1"

    r = await client.post(
        f"/api/v1/site/page-llm-extractions/by-page/{a['id']}/page-type",
        json={"pageType": "money"},
    )
    assert r.status_code == 409

    r = await client.get(f"/api/v1/site/page-llm-extractions/by-page/{a['id']}")
    assert r.json()["data"]["pageType"] == "hub"

    assert await site_page_classifier.run_extraction_pass(site["id"]) == 0


async def test_set_page_type_on_a_page_never_extracted(client, site):
    a = await add_page(client, "https://extract.example.com/new", bodyText="x", contentHash="h9")
    r = await client.post(
        f"/api/v1/site/page-llm-extractions/by-page/{a['id']}/page-type",
        json={"pageType": "legal"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["pageType"] == "legal"
    assert r.json()["data"]["extractedFromHash"] == "h9"

    r = await client.post(
        "/api/v1/site/page-llm-extractions/by-page/pg_missing/page-type",
        json={"pageType": "legal"},
    )
    assert r.status_code == 404
