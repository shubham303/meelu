from httpx import ASGITransport, AsyncClient

from tests.conftest import signup


async def test_session_creates_user_once(client, email):
    r = await signup(client, email, name="Grace Hopper")
    body = r.json()["data"]
    assert body["created"] is True
    user = body["user"]
    assert user["email"] == email
    assert user["name"] == "Grace Hopper"
    assert user["id"].startswith("user_")
    assert "authId" not in user

    r = await signup(client, email, name="Grace Hopper")
    again = r.json()["data"]
    assert again["created"] is False
    assert again["user"]["id"] == user["id"]


async def test_session_rejects_bad_token(client):
    r = await client.post("/api/auth/session", json={"accessToken": "garbage"})
    assert r.status_code == 401
    assert r.json() == {"error": {"message": "The sign-in token is invalid or expired."}}


async def test_session_links_existing_email(client, email):
    from src.core.database import unit_of_work
    from src.profile.repository import users

    async with unit_of_work() as db:
        await users.create(db, "sb-old", email, "Old", None, True)
        await users.update(db, (await users.find_by_email(db, email)).id, {"auth_id": None})

    r = await signup(client, email)
    assert r.json()["data"]["created"] is False

    async with unit_of_work() as db:
        assert (await users.find_by_email(db, email)).auth_id == f"sb-{email}"


async def test_session_cookie_flow(client, email):
    await signup(client, email, name="Ada Lovelace")

    r = await client.get("/api/v1/profile")
    assert r.status_code == 200
    profile = r.json()["data"]
    assert profile["fullName"] == "Ada Lovelace"

    r = await client.get("/api/v1/keys")
    assert r.status_code == 200
    keys = r.json()["data"]
    assert len(keys) == 1
    assert keys[0]["name"] == "Default MCP key"
    assert keys[0].get("lastUsedAt") is None
    assert "keyHash" not in keys[0]
    assert "userId" not in keys[0]
    assert "seq" not in keys[0]


async def test_me_returns_current_user(client, email):
    await signup(client, email, name="Ada Lovelace")

    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    user = r.json()["data"]
    assert user["email"] == email
    assert user["name"] == "Ada Lovelace"
    assert user.get("image") is None
    assert user["id"].startswith("user_")
    assert "hashedPassword" not in user
    assert "authId" not in user


async def test_me_unauthenticated(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json() == {"error": {"message": "Not authenticated."}}


async def test_unauthenticated_error_shape(client):
    r = await client.get("/api/v1/keys")
    assert r.status_code == 401
    assert r.json() == {
        "error": {"message": "Not authenticated. Sign in or pass an x-api-key header."}
    }


async def test_api_key_auth(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/keys", json={"name": "harness"})
    assert r.status_code == 201
    created = r.json()["data"]
    raw = created["key"]
    assert raw.startswith("emcp_")
    assert len(raw) == 5 + 64
    assert created["preview"] == f"{raw[:9]}…{raw[-4:]}"

    from src.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as fresh:
        r = await fresh.get("/api/v1/profile", headers={"x-api-key": raw})
        assert r.status_code == 200

        r = await fresh.get("/api/v1/profile", headers={"x-api-key": "emcp_wrong"})
        assert r.status_code == 401
        assert r.json() == {"error": {"message": "Invalid API key."}}

    r = await client.get("/api/v1/keys")
    used = next(k for k in r.json()["data"] if k["name"] == "harness")
    assert used["lastUsedAt"] is not None


async def test_logout(client, email):
    await signup(client, email)
    r = await client.post("/api/auth/logout")
    assert r.status_code == 204

    r = await client.get("/api/v1/keys")
    assert r.status_code == 401
