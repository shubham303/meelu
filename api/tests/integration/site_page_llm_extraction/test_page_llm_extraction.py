import asyncio

import pytest

from src.providers.errors import ProviderRequestError
from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import VendorResponse
from src.site_page_llm_extraction import classify
from tests.conftest import signup


@pytest.fixture(scope="session", autouse=True)
def mount_routes():
    from src.app import app
    from src.site_page_llm_extraction.endpoints import router
    from src.site_pages.endpoints import router as pages_router

    for r in (router, pages_router):
        if not any(getattr(x, "original_router", None) is r for x in app.routes):
            app.include_router(r, prefix="/api/v1")


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


async def wait_idle(site_id):
    for _ in range(200):
        if not classify.running(site_id):
            return
        await asyncio.sleep(0.05)
    raise AssertionError("classification never finished")


async def test_run_classifies_pending_pages(client, site, jev):
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
    assert r.json()["data"]["stats"] == {
        "eligible": 3,
        "extracted": 0,
        "pending": 3,
        "running": False,
    }

    r = await client.post("/api/v1/site/page-llm-extractions/run")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["started"] is True
    await wait_idle(site["id"])

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
    assert r.json()["data"]["pageType"] is None
    assert "jev down" in r.json()["data"]["error"]

    r = await client.get("/api/v1/site/page-llm-extractions/stats")
    assert r.json()["data"]["stats"]["extracted"] == 2
    assert r.json()["data"]["stats"]["pending"] == 1

    r = await client.get("/api/v1/site/page-llm-extractions?page_type=money")
    assert [x["pageId"] for x in r.json()["data"]] == [b["id"]]

    r = await client.post("/api/v1/site/page-llm-extractions/run")
    await wait_idle(site["id"])
    assert len(jev.calls) == 4

    r = await client.get("/api/v1/providers/calls?domain=json-data-extractor")
    assert r.status_code == 200, r.text
    calls = r.json()["data"]
    assert len(calls) == 4
    assert {c["status"] for c in calls} == {"ok", "error"}

    r = await client.patch(f"/api/v1/site/pages/{a['id']}", json={"contentHash": "h1-new"})
    assert r.status_code == 200, r.text
    r = await client.get("/api/v1/site/page-llm-extractions/stats")
    assert r.json()["data"]["stats"]["pending"] == 2


async def test_run_with_nothing_pending_does_not_start(client, site, jev):
    r = await client.post("/api/v1/site/page-llm-extractions/run")
    assert r.json()["data"] == {"started": False, "running": False, "pending": 0}
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
