import pytest
from sqlalchemy import select

from src.core.database import unit_of_work
from src.core.ids import uid
from src.embed_worker import models
from src.embed_worker.search.service import page_search_service
from src.site_pages.models.site_chunk import SiteChunk
from src.sites.models.site import Site
from tests.integration.site_pages.conftest import save_page, save_pages


def loaded_embedder():
    try:
        from src.embed_worker.embedding import Embedder

        return Embedder(models.embed_model())
    except Exception:
        return None


async def add_chunk(site, page, text, heading_path=None, vector=None):
    async with unit_of_work() as db:
        row = (await db.execute(select(Site).where(Site.id == site["id"]))).scalar_one()
        db.add(
            SiteChunk(
                id=uid("chk"),
                user_id=row.user_id,
                site_id=site["id"],
                page_id=page["id"],
                ordinal=0,
                heading_path=heading_path,
                text=text,
                embedding=vector,
                embed_model=models.embed_model() if vector is not None else None,
            )
        )


async def test_search_without_text_is_keyword_listing(client, site):
    await save_pages(
        client,
        [
            {"url": "https://example.com/espresso", "status": 200, "title": "Espresso"},
            {"url": "https://example.com/tea", "status": 200, "title": "Tea"},
        ],
    )

    r = await client.get("/api/v1/site/pages", params={"titleContains": "espresso"})
    body = r.json()
    assert [p["url"] for p in body["data"]] == ["https://example.com/espresso"]
    assert body.get("note") is None


async def test_min_similarity_default():
    assert page_search_service.default_min_similarity() == 0.82


async def test_search_requires_text(client, site):
    r = await client.post("/api/v1/site/pages/search", json={"text": "  "})
    assert r.status_code == 400


async def test_keyword_search_works_without_models(client, site, monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")
    monkeypatch.setenv("MEELU_RERANK_DISABLED", "1")
    grinders = await save_page(
        client, url="https://example.com/grinders", status=200, title="Burr grinders"
    )
    tea = await save_page(client, url="https://example.com/tea", status=200, title="Tea")
    await add_chunk(site, grinders, "Burr grinders crush beans between two burrs.", "Grinders")
    await add_chunk(site, tea, "Green tea steeps at a lower temperature.", "Tea")

    r = await client.post(
        "/api/v1/site/pages/search", json={"text": "burr grinders", "mode": "keyword"}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["mode"] == "keyword"
    assert body["reranked"] is False
    assert [h["url"] for h in body["hits"]] == ["https://example.com/grinders"]
    hit = body["hits"][0]
    assert hit["pageId"] == grinders["id"]
    assert hit["keywordRank"] == 1
    assert hit.get("similarity") is None
    assert hit["snippet"] == "Burr grinders crush beans between two burrs."
    assert hit["headingPath"] == "Grinders"

    r = await client.post("/api/v1/site/pages/search", json={"text": "burr grinders"})
    body = r.json()["data"]
    assert body["mode"] == "keyword"
    assert body["note"] == "Keyword search only — the embedding model is unavailable."
    assert [h["url"] for h in body["hits"]] == ["https://example.com/grinders"]

    r = await client.post(
        "/api/v1/site/pages/search", json={"text": "burr grinders", "mode": "semantic"}
    )
    body = r.json()["data"]
    assert body["hits"] == []
    assert body["note"] == "Semantic search is unavailable — the text could not be embedded."


async def test_search_from_text_uses_any_term(client, site, monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")
    monkeypatch.setenv("MEELU_RERANK_DISABLED", "1")
    grinders = await save_page(client, url="https://example.com/grinders", status=200)
    await add_chunk(site, grinders, "Burr grinders crush beans between two burrs.")

    passage = "A long paragraph about kettles that also mentions burrs once, nothing else."
    r = await client.post(
        "/api/v1/site/pages/search", json={"text": passage, "input": "text", "mode": "keyword"}
    )
    assert [h["url"] for h in r.json()["data"]["hits"]] == ["https://example.com/grinders"]

    r = await client.post(
        "/api/v1/site/pages/search", json={"text": passage, "input": "query", "mode": "keyword"}
    )
    assert r.json()["data"]["hits"] == []


async def test_listing_search_falls_back_to_keyword(client, site, monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")
    monkeypatch.setenv("MEELU_RERANK_DISABLED", "1")
    grinders = await save_page(client, url="https://example.com/grinders", status=200)
    await add_chunk(site, grinders, "Burr grinders crush beans.", "Grinders")

    r = await client.get("/api/v1/site/pages", params={"searchText": "grinders"})
    assert r.status_code == 200
    body = r.json()
    assert [p["url"] for p in body["data"]] == ["https://example.com/grinders"]
    assert body["data"][0]["match"] == {
        "text": "Burr grinders crush beans.",
        "headingPath": "Grinders",
    }
    assert body["note"] == "Keyword search only — the embedding model is unavailable."


async def test_hybrid_search_with_models(client, site, monkeypatch):
    embedder = loaded_embedder()
    if embedder is None:
        pytest.skip("embedding model is not available offline")
    monkeypatch.setenv("MEELU_RERANK_DISABLED", "1")

    grinders = await save_page(
        client, url="https://example.com/grinders", status=200, title="Burr grinders"
    )
    tea = await save_page(client, url="https://example.com/tea", status=200, title="Tea")

    r = await client.post("/api/v1/site/pages/search", json={"text": "burr grinder"})
    body = r.json()["data"]
    assert body["hits"] == []
    assert body["mode"] == "hybrid"
    assert body["note"] == (
        "Nothing is embedded for this website yet, so a semantic search cannot see any page."
    )

    passage = "Burr grinders crush beans between two burrs for an even espresso grind."
    await add_chunk(
        site, grinders, passage, "Burr grinders", embedder.embed([f"passage: {passage}"])[0]
    )
    await add_chunk(site, tea, "Green tea steeps at a lower temperature.", "Tea")

    r = await client.post(
        "/api/v1/site/pages/search", json={"text": "burr grinder", "minSimilarity": 0.0}
    )
    body = r.json()["data"]
    assert [h["url"] for h in body["hits"]] == ["https://example.com/grinders"]
    hit = body["hits"][0]
    assert hit["similarity"] > 0.5
    assert hit["keywordRank"] == 1
    assert body["note"] == "Semantic coverage is partial: 1 of 2 passages embedded."

    r = await client.post(
        "/api/v1/site/pages/search",
        json={"text": "burr grinder", "mode": "semantic", "minSimilarity": 0.99},
    )
    assert r.json()["data"]["hits"] == []

    r = await client.get(
        "/api/v1/site/pages", params={"searchText": "burr grinder", "pageType": "nothing"}
    )
    assert r.json()["data"] == []


async def test_rerank_scores_hits(client, site, monkeypatch):
    if models.reranker.get() is None:
        pytest.skip("rerank model is not available offline")
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")

    grinders = await save_page(client, url="https://example.com/grinders", status=200)
    kettles = await save_page(client, url="https://example.com/kettles", status=200)
    await add_chunk(site, grinders, "Burr grinders crush coffee beans evenly for espresso.")
    await add_chunk(site, kettles, "Gooseneck kettles pour slowly; grinders are sold separately.")

    r = await client.post(
        "/api/v1/site/pages/search", json={"text": "how do burr grinders work", "mode": "keyword"}
    )
    body = r.json()["data"]
    assert body["reranked"] is True
    assert [h["url"] for h in body["hits"]] == [
        "https://example.com/grinders",
        "https://example.com/kettles",
    ]
    assert body["hits"][0]["rerankScore"] > body["hits"][1]["rerankScore"]
