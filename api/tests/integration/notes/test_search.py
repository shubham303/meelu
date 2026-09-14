import pytest

from tests.conftest import signup

HIT_FIELDS = {
    "id",
    "siteId",
    "note",
    "kind",
    "createdAt",
    "updatedAt",
    "score",
    "similarity",
}

FIXTURE_NOTES = [
    ("The checkout flow must never ask for a phone number.", "note"),
    ("Checkout copy stays plain, no marketing checkout language.", "note"),
    ("Pricing tables belong above the fold.", "note"),
    ("Do not call the readers customers.", "feedback"),
]


async def seed(client, email, *, disabled: bool):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "search.example", "name": "Search"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    for note, kind in FIXTURE_NOTES:
        r = await client.post("/api/v1/notes", json={"note": note, "kind": kind})
        assert r.status_code == 201, r.text
    return site


async def test_keyword_search_ranking(client, email, monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")
    await seed(client, email, disabled=True)

    r = await client.get("/api/v1/notes", params={"q": "checkout"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert set(body) == {"hits", "mode", "embedded", "note"}
    assert body["mode"] == "keyword"
    assert body["embedded"] == {"done": 0, "total": 4}
    assert body["note"] == (
        "Keyword search only — semantic search is unavailable (0 of 4 notes embedded)."
    )

    hits = body["hits"]
    assert len(hits) == 2
    assert set(hits[0]) == HIT_FIELDS
    assert all(h["similarity"] is None for h in hits)
    assert hits[0]["score"] >= hits[1]["score"]
    assert "checkout" in hits[0]["note"].lower()
    assert hits[0]["note"].lower().count("checkout") == 2

    r = await client.get("/api/v1/notes", params={"q": "checkout", "kind": "feedback"})
    assert r.json()["data"]["hits"] == []

    r = await client.get("/api/v1/notes", params={"q": "customers", "kind": "feedback"})
    hits = r.json()["data"]["hits"]
    assert len(hits) == 1
    assert hits[0]["kind"] == "feedback"

    r = await client.get("/api/v1/notes", params={"q": "checkout", "limit": 1})
    assert len(r.json()["data"]["hits"]) == 1

    r = await client.get("/api/v1/notes", params={"q": "checkout", "mode": "keyword"})
    body = r.json()["data"]
    assert body["mode"] == "keyword"
    assert body["note"] == "Semantic coverage is partial: 0 of 4 notes embedded."

    r = await client.get("/api/v1/notes", params={"q": "zzzznothing"})
    assert r.json()["data"]["hits"] == []

    r = await client.get("/api/v1/notes", params={"q": "checkout", "kind": "rumour"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": 'Invalid kind "rumour". Allowed values: note, feedback.'}
    }


async def test_search_without_notes_reports_empty_coverage(client, email, monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "empty.example", "name": "Empty"})
    assert r.status_code == 201

    r = await client.get("/api/v1/notes", params={"q": "anything"})
    body = r.json()["data"]
    assert body["hits"] == []
    assert body["mode"] == "keyword"
    assert body["embedded"] == {"done": 0, "total": 0}
    assert body["note"] == "Keyword search only — no notes are embedded for this website yet."


async def test_hybrid_search(client, email):
    from src.notes import embedder

    if await embedder.embed_query("probe") is None:
        pytest.skip("embedding model unavailable offline")

    await seed(client, email, disabled=False)

    r = await client.get("/api/v1/notes", params={"q": "checkout"})
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["mode"] == "hybrid"
    assert body["embedded"] == {"done": 4, "total": 4}
    assert "note" not in body

    hits = body["hits"]
    assert hits
    assert set(hits[0]) == HIT_FIELDS
    assert any(h["similarity"] is not None for h in hits)
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)

    r = await client.get("/api/v1/notes", params={"q": "checkout", "mode": "semantic"})
    body = r.json()["data"]
    assert body["mode"] == "semantic"
    assert all(h["similarity"] is not None for h in body["hits"])

    r = await client.get("/api/v1/notes", params={"q": "checkout", "mode": "keyword"})
    assert r.json()["data"]["mode"] == "keyword"
