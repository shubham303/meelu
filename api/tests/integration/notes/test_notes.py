import pytest

from tests.conftest import signup

NOTE_FIELDS = {"id", "siteId", "note", "kind", "createdAt", "updatedAt"}


@pytest.fixture(autouse=True)
def no_embeddings(monkeypatch):
    monkeypatch.setenv("MEELU_EMBED_DISABLED", "1")


async def make_site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "notes.example", "name": "Notes"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_notes_crud(client, email):
    site = await make_site(client, email)

    r = await client.post("/api/v1/notes", json={"note": "Always use the Oxford comma."})
    assert r.status_code == 201, r.text
    note = r.json()["data"]
    assert set(note) == NOTE_FIELDS
    assert note["note"] == "Always use the Oxford comma."
    assert note["kind"] == "note"
    assert note["siteId"] == site["id"]

    r = await client.post(
        "/api/v1/notes", json={"note": "  Never say synergy.  ", "kind": "feedback"}
    )
    assert r.status_code == 201
    feedback = r.json()["data"]
    assert feedback["note"] == "Never say synergy."
    assert feedback["kind"] == "feedback"

    r = await client.post("/api/v1/notes", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "A note needs some text."}}

    r = await client.post("/api/v1/notes", json={"note": "hi", "kind": "rumour"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": 'Invalid kind "rumour". Allowed values: note, feedback.'}
    }

    r = await client.post("/api/v1/notes", json={"note": "x" * 4001})
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith(
        "That note is 4001 characters — keep it under 4000."
    )

    r = await client.get("/api/v1/notes")
    assert r.status_code == 200
    body = r.json()["data"]
    assert set(body) == {"notes", "total", "shown", "offset"}
    assert body["total"] == 2
    assert body["shown"] == 2
    assert body["offset"] == 0
    assert body["notes"][0]["id"] == feedback["id"]

    r = await client.get(f"/api/v1/notes/{note['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == note["id"]

    r = await client.get("/api/v1/notes/note_missing")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.put(f"/api/v1/notes/{note['id']}", json={"note": "Skip the Oxford comma."})
    assert r.status_code == 200
    updated = r.json()["data"]
    assert updated["note"] == "Skip the Oxford comma."
    assert updated["kind"] == "note"

    r = await client.patch(f"/api/v1/notes/{note['id']}", json={"kind": "feedback"})
    assert r.status_code == 200
    assert r.json()["data"]["kind"] == "feedback"

    r = await client.put(f"/api/v1/notes/{note['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Nothing to save."}}

    r = await client.put("/api/v1/notes/note_missing", json={"note": "nope"})
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/notes/{note['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"id": note["id"]}}

    r = await client.delete(f"/api/v1/notes/{note['id']}")
    assert r.status_code == 404

    r = await client.get("/api/v1/notes")
    assert r.json()["data"]["total"] == 1


async def test_notes_filters(client, email):
    await make_site(client, email)

    for text, kind in [
        ("Checkout copy stays plain.", "note"),
        ("Pricing page needs a table.", "note"),
        ("Do not call users customers.", "feedback"),
    ]:
        r = await client.post("/api/v1/notes", json={"note": text, "kind": kind})
        assert r.status_code == 201

    r = await client.get("/api/v1/notes", params={"kind": "feedback"})
    body = r.json()["data"]
    assert body["total"] == 1
    assert body["notes"][0]["kind"] == "feedback"

    r = await client.get("/api/v1/notes", params={"kind": "note,feedback"})
    assert r.json()["data"]["total"] == 3

    r = await client.get("/api/v1/notes", params={"contains": "pricing"})
    body = r.json()["data"]
    assert body["total"] == 1
    assert "Pricing" in body["notes"][0]["note"]

    r = await client.get("/api/v1/notes", params={"limit": 2})
    body = r.json()["data"]
    assert body["total"] == 3
    assert body["shown"] == 2
    assert body["offset"] == 0

    r = await client.get("/api/v1/notes", params={"limit": 2, "offset": 2})
    body = r.json()["data"]
    assert body["shown"] == 1
    assert body["offset"] == 2

    r = await client.get("/api/v1/notes", params={"sort": "updated"})
    assert r.status_code == 200
    r = await client.get("/api/v1/notes", params={"sort": "sideways"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "sort must be one of created, updated."}}

    r = await client.get("/api/v1/notes", params={"createdAfter": "2100-01-01"})
    assert r.json()["data"]["total"] == 0
    r = await client.get("/api/v1/notes", params={"createdBefore": "2100-01-01"})
    assert r.json()["data"]["total"] == 3
    r = await client.get("/api/v1/notes", params={"createdAfter": "not a date"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "createdAfter must be a date or ISO timestamp."}}


async def test_agent_mcp_contract(client, email):
    site = await make_site(client, email)

    r = await client.post("/api/v1/keys", json={"name": "agent"})
    assert r.status_code == 201
    api_key = r.json()["data"]["key"]

    client.cookies.clear()
    headers = {"x-api-key": api_key, "x-meelu-site": site["id"]}

    r = await client.post(
        "/api/v1/notes", json={"note": "Ship on Tuesdays.", "kind": "note"}, headers=headers
    )
    assert r.status_code == 201, r.text
    payload = r.json()
    assert set(payload) == {"data"}
    saved = payload["data"]
    assert set(saved) == NOTE_FIELDS
    assert saved["id"].startswith("note_")
    assert saved["siteId"] == site["id"]
    assert saved["note"] == "Ship on Tuesdays."
    assert saved["kind"] == "note"
    assert saved["createdAt"].endswith("Z")
    assert saved["updatedAt"].endswith("Z")

    r = await client.put(
        f"/api/v1/notes/{saved['id']}",
        json={"note": "Ship on Wednesdays.", "kind": "feedback"},
        headers=headers,
    )
    assert r.status_code == 200
    edited = r.json()["data"]
    assert set(edited) == NOTE_FIELDS
    assert edited["id"] == saved["id"]
    assert edited["note"] == "Ship on Wednesdays."
    assert edited["kind"] == "feedback"

    r = await client.delete(f"/api/v1/notes/{saved['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"data": {"id": saved["id"]}}

    r = await client.delete(f"/api/v1/notes/{saved['id']}", headers=headers)
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.get("/api/v1/notes", headers={"x-api-key": "emcp_wrong"})
    assert r.status_code == 401
    assert r.json() == {"error": {"message": "Invalid API key."}}
