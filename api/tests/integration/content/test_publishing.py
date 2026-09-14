from tests.integration.content.publishing import channel_enabled

NO_ACCOUNT = {"error": {"message": "This website has no publishing account yet."}}


async def test_account_404_when_none(client, workspace):
    r = await client.get("/api/v1/social/account")
    assert r.status_code == 404
    assert r.json() == NO_ACCOUNT

    r = await client.delete("/api/v1/social/account")
    assert r.status_code == 404
    assert r.json() == NO_ACCOUNT


async def test_account_requires_fields(client, workspace):
    r = await client.put("/api/v1/social/account", json={})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Missing required field(s): provider, externalAccountId"}
    }

    r = await client.put(
        "/api/v1/social/account", json={"provider": "postproxy", "externalAccountId": " "}
    )
    assert r.status_code == 400
    assert "must be non-empty" in r.json()["error"]["message"]


async def test_account_upsert_get_delete(client, workspace):
    r = await client.put(
        "/api/v1/social/account", json={"provider": "postproxy", "externalAccountId": "pg_1"}
    )
    assert r.status_code == 200
    created = r.json()["data"]
    assert created["provider"] == "postproxy"
    assert created["externalAccountId"] == "pg_1"
    assert set(created) == {"id", "provider", "externalAccountId"}

    r = await client.put(
        "/api/v1/social/account", json={"provider": "postproxy", "externalAccountId": "pg_2"}
    )
    assert r.status_code == 200
    assert r.json()["data"] == {**created, "externalAccountId": "pg_2"}

    r = await client.get("/api/v1/social/account")
    assert r.status_code == 200
    assert r.json()["data"] == {**created, "externalAccountId": "pg_2"}

    r = await client.delete("/api/v1/social/account")
    assert r.status_code == 200
    assert r.json()["data"] == {"deleted": True}

    r = await client.get("/api/v1/social/account")
    assert r.status_code == 404


async def test_channels_sync_enables_active_platforms(client, workspace):
    r = await client.post("/api/v1/social/channels/sync", json={"platforms": ["linkedin", ""]})
    assert r.status_code == 200
    assert r.json()["data"] == {"synced": True}
    assert await channel_enabled(workspace, "linkedin") is True
    assert await channel_enabled(workspace, "twitter") is False

    r = await client.post("/api/v1/social/channels/sync", json={})
    assert r.status_code == 200
    assert await channel_enabled(workspace, "linkedin") is False
    assert await channel_enabled(workspace, "website") is True
