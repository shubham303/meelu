from tests.conftest import signup


async def test_keys_crud(client, email):
    await signup(client, email)

    r = await client.post("/api/v1/keys", json={})
    assert r.status_code == 201
    created = r.json()["data"]
    assert created["name"] == "MCP key"
    assert set(created) == {"id", "name", "preview", "lastUsedAt", "createdAt", "updatedAt", "key"}

    r = await client.get("/api/v1/keys")
    keys = r.json()["data"]
    assert len(keys) == 2
    assert keys[0]["id"] == created["id"]

    r = await client.delete(f"/api/v1/keys/{created['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"id": created["id"], "deleted": True}}

    r = await client.delete(f"/api/v1/keys/{created['id']}")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.get("/api/v1/keys")
    last = r.json()["data"][0]
    r = await client.delete(f"/api/v1/keys/{last['id']}")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Cannot revoke the last remaining API key."}}
