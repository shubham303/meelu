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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as fresh:
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


async def deactivate(email):
    from src.core.database import unit_of_work
    from src.profile.repository import users

    async with unit_of_work() as db:
        user = await users.find_by_email(db, email)
        await users.update(db, user.id, {"is_active": False})


async def test_api_key_of_inactive_user_is_refused(client, email):
    await signup(client, email)
    raw = (await client.post("/api/v1/keys", json={"name": "harness"})).json()["data"]["key"]
    await deactivate(email)

    from src.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as fresh:
        r = await fresh.get("/api/v1/profile", headers={"x-api-key": raw})
        assert r.status_code == 401

    import pytest
    from fastapi import HTTPException

    from src.agent.auth import resolve

    with pytest.raises(HTTPException) as refused:
        await resolve(raw, None)
    assert refused.value.status_code == 401


async def test_unconfirmed_email_cannot_sign_in(client, email, monkeypatch):
    from src.identity import supabase

    async def unconfirmed(access_token: str) -> supabase.SupabaseUser:
        return supabase.SupabaseUser(
            id=f"sb-{email}", email=email, name="", image=None, email_confirmed=False
        )

    monkeypatch.setattr(supabase, "fetch_user", unconfirmed)
    r = await client.post("/api/auth/session", json={"accessToken": "anything"})
    assert r.status_code == 403
    assert r.json() == {"error": {"message": "Confirm your email address before signing in."}}


async def test_session_cookie_is_secure_and_stored_hashed(client, email):
    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.keys.repository import hash_key
    from src.profile.models.user import AccessToken

    r = await signup(client, email)
    set_cookie = r.headers["set-cookie"]
    assert "Secure" in set_cookie and "HttpOnly" in set_cookie
    token = client.cookies.get("meelu_session")

    async with unit_of_work() as db:
        stored = (await db.execute(select(AccessToken.token_hash))).scalars().all()
    assert hash_key(token) in stored
    assert token not in stored

    r = await client.post("/api/auth/logout")
    assert "Secure" in r.headers["set-cookie"]


async def test_expired_sessions_are_purged(client, email):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select, update

    from src.core.database import unit_of_work
    from src.identity.service import identity_service
    from src.keys.repository import hash_key
    from src.profile.models.user import AccessToken
    from src.settings import settings

    await signup(client, email)
    digest = hash_key(client.cookies.get("meelu_session"))
    async with unit_of_work() as db:
        await db.execute(
            update(AccessToken)
            .where(AccessToken.token_hash == digest)
            .values(
                created_at=datetime.now(UTC)
                - timedelta(seconds=settings.session_lifetime_seconds + 60)
            )
        )
    async with unit_of_work() as db:
        assert await identity_service.purge_expired_sessions(db) >= 1
    async with unit_of_work() as db:
        left = await db.execute(select(AccessToken).where(AccessToken.token_hash == digest))
        assert left.first() is None


async def test_cross_site_cookie_writes_are_refused(client, email):
    await signup(client, email)

    r = await client.post(
        "/api/v1/keys",
        json={"name": "evil"},
        headers={"origin": "https://evil.example", "sec-fetch-site": "cross-site"},
    )
    assert r.status_code == 403

    r = await client.post(
        "/api/v1/keys", json={"name": "no-fetch-site"}, headers={"origin": "https://evil.example"}
    )
    assert r.status_code == 403

    r = await client.post(
        "/api/v1/keys",
        json={"name": "dashboard"},
        headers={"origin": "https://app.meelu.tech", "sec-fetch-site": "same-origin"},
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/v1/keys",
        json={"name": "listed origin"},
        headers={"origin": "http://localhost:3000", "sec-fetch-site": "same-site"},
    )
    assert r.status_code == 201

    r = await client.post("/api/v1/keys", json={"name": "node client"})
    assert r.status_code == 201


async def test_api_docs_are_off_by_default(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        r = await client.get(path)
        assert r.status_code == 404


def test_cors_origins_reject_wildcard():
    import pytest
    from pydantic import ValidationError

    from src.settings import Settings

    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"])


async def test_session_rejects_empty_token(client):
    r = await client.post("/api/auth/session", json={"accessToken": ""})
    assert r.status_code == 400


async def test_supabase_failures_map_to_401_or_503(monkeypatch):
    import httpx
    import pytest

    from src.identity import supabase
    from src.settings import settings

    monkeypatch.undo()
    real = supabase.fetch_user
    monkeypatch.setattr(settings, "supabase_url", "https://supabase.test")
    monkeypatch.setattr(settings, "supabase_publishable_key", "anon")

    original = httpx.AsyncClient

    def respond_with(handler):
        transport = httpx.MockTransport(handler)

        def client(*args, **kwargs):
            return original(*args, **{**kwargs, "transport": transport})

        monkeypatch.setattr(httpx, "AsyncClient", client)

    def down(request):
        raise httpx.ConnectError("refused", request=request)

    cases = [
        (lambda r: httpx.Response(401, json={"msg": "bad jwt"}), supabase.SupabaseAuthError),
        (lambda r: httpx.Response(200, text="<html>"), supabase.SupabaseUnavailableError),
        (lambda r: httpx.Response(502, text="bad gateway"), supabase.SupabaseUnavailableError),
        (down, supabase.SupabaseUnavailableError),
    ]
    for handler, expected in cases:
        respond_with(handler)
        with pytest.raises(expected):
            await real("token")

    def malformed(request):
        raise httpx.LocalProtocolError("Illegal header value")

    respond_with(malformed)
    with pytest.raises(supabase.SupabaseAuthError):
        await real("bad\ntoken")
    with pytest.raises(supabase.SupabaseAuthError):
        await real("   ")
