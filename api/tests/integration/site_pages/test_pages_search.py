import pytest

from src.site_pages import embedding, repository
from tests.integration.site_pages.conftest import save_page, save_pages


@pytest.fixture(autouse=True)
def reset_embedder():
    embedding._state[0] = False
    embedding._state[1] = None
    yield
    embedding._state[0] = False
    embedding._state[1] = None


def loaded_embedder():
    try:
        from src.embed_worker.embedding import Embedder

        return Embedder(embedding.EMBED_MODEL)
    except Exception:
        return None


async def test_search_without_text_is_keyword_listing(client, site):
    await save_pages(
        client,
        [
            {"url": "https://example.com/espresso", "status": 200, "title": "Espresso"},
            {"url": "https://example.com/tea", "status": 200, "title": "Tea"},
        ],
    )

    r = await client.get("/api/v1/site/pages", params={"titleContains": "espresso"})
    body = r.json()["data"]
    assert [p["url"] for p in body["pages"]] == ["https://example.com/espresso"]
    assert "note" not in body


async def test_search_is_unavailable_when_embedding_disabled(client, site, monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")
    await save_page(client, url="https://example.com/a", status=200)

    r = await client.get("/api/v1/site/pages", params={"searchText": "grinders"})
    assert r.status_code == 503
    assert r.json() == {
        "error": {"message": "Semantic search is unavailable — the query could not be embedded."}
    }


async def test_min_similarity_default():
    assert repository.MIN_SIMILARITY == 0.82


async def test_semantic_search_notes_and_matches(client, site, monkeypatch):
    embedder = loaded_embedder()
    if embedder is None:
        pytest.skip("embedding model is not available offline")

    page = await save_page(
        client, url="https://example.com/grinders", status=200, title="Burr grinders"
    )
    await save_page(client, url="https://example.com/tea", status=200, title="Tea")

    r = await client.get("/api/v1/site/pages", params={"searchText": "burr grinder"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["pages"] == []
    assert body["total"] == 0
    assert body["shown"] == 0
    assert body["note"] == (
        "Nothing is embedded for this website yet, so a semantic search cannot see any page."
    )

    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_chunk import SiteChunk
    from src.sites.models.site import Site

    passage = "Burr grinders crush beans between two burrs for an even espresso grind."
    vector = embedder.embed([f"passage: {passage}"])[0]

    async with unit_of_work() as db:
        row = (await db.execute(select(Site).where(Site.id == site["id"]))).scalar_one()
        db.add(
            SiteChunk(
                id=uid("chk"),
                user_id=row.user_id,
                site_id=site["id"],
                page_id=page["id"],
                ordinal=0,
                heading_path="Burr grinders",
                text=passage,
                embedding=vector,
                embed_model=embedding.EMBED_MODEL,
            )
        )

    monkeypatch.setattr(repository, "MIN_SIMILARITY", 0.0)

    r = await client.get("/api/v1/site/pages", params={"searchText": "burr grinder"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert [p["url"] for p in body["pages"]] == ["https://example.com/grinders"]
    hit = body["pages"][0]
    assert hit["similarity"] > 0.5
    assert hit["match"] == {"text": passage, "headingPath": "Burr grinders"}

    r = await client.get(
        "/api/v1/site/pages", params={"searchText": "burr grinder", "kind": "nothing"}
    )
    assert r.json()["data"]["pages"] == []


async def test_semantic_search_reports_partial_coverage(client, site, monkeypatch):
    embedder = loaded_embedder()
    if embedder is None:
        pytest.skip("embedding model is not available offline")

    page = await save_page(client, url="https://example.com/p", status=200)

    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_chunk import SiteChunk
    from src.sites.models.site import Site

    async with unit_of_work() as db:
        row = (await db.execute(select(Site).where(Site.id == site["id"]))).scalar_one()
        db.add(
            SiteChunk(
                id=uid("chk"),
                user_id=row.user_id,
                site_id=site["id"],
                page_id=page["id"],
                ordinal=0,
                text="not embedded yet",
            )
        )

    r = await client.get("/api/v1/site/pages", params={"searchText": "anything at all"})
    assert r.status_code == 200
    assert r.json()["data"]["note"] == (
        "No page matches. Semantic coverage is partial: 0 of 1 passages embedded."
    )
