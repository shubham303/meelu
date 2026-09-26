from httpx import ASGITransport, AsyncClient

from tests.conftest import signup


async def test_register_returns_user_envelope(client, email):
    r = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "secret123", "name": "Grace Hopper"},
    )
    assert r.status_code == 201
    user = r.json()["data"]
    assert user["email"] == email
    assert user["name"] == "Grace Hopper"
    assert user.get("image") is None
    assert user["id"].startswith("user_")
    assert "hashedPassword" not in user
    assert "hashed_password" not in user


async def test_register_duplicate_email(client, email):
    await signup(client, email)
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": "secret123", "name": "X"}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "An account with this email already exists."}}


async def test_login_wrong_credentials(client, email):
    await signup(client, email)

    r = await client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Wrong email or password."}}

    r = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "secret123"}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Wrong email or password."}}


async def test_register_login_cookie_flow(client, email):
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
    assert "hashed_password" not in user


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


async def test_register_rejects_short_password(client, email):
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": "abc", "name": "X"}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Password should be at least 6 characters long."}}
