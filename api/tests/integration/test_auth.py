import json

from httpx import ASGITransport, AsyncClient

from tests.conftest import mint_token, signup


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
        await users.create(db, "old-provider-id", email, "Old", None, True)
        await users.update(db, (await users.find_by_email(db, email)).id, {"auth_id": None})

    r = await signup(client, email)
    assert r.json()["data"]["created"] is False

    async with unit_of_work() as db:
        assert (await users.find_by_email(db, email)).auth_id == f"ba-{email}"


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


async def test_unconfirmed_email_cannot_sign_in(client, email):
    r = await client.post(
        "/api/auth/session", json={"accessToken": mint_token(email, verified=False)}
    )
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


async def test_session_rejects_tokens_that_fail_verification(client, email):
    import time

    import jwt
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    now = int(time.time())
    rejected = [
        mint_token(email, exp=now - 10, iat=now - 400),
        mint_token(email, iss="https://evil.test"),
        mint_token(email, aud="https://evil.test"),
        mint_token(email, key=Ed25519PrivateKey.generate()),
        mint_token(email, kid="unknown-key"),
        mint_token(""),
        jwt.encode(
            {"sub": "x", "email": email}, key=None, algorithm="none", headers={"kid": "test-key"}
        ),
        jwt.encode(
            {"sub": "x", "email": email}, "secret", algorithm="HS256", headers={"kid": "test-key"}
        ),
    ]
    for token in rejected:
        r = await client.post("/api/auth/session", json={"accessToken": token})
        assert r.status_code == 401, token
        assert r.json() == {"error": {"message": "The sign-in token is invalid or expired."}}


async def test_unknown_kid_refreshes_the_key_set(monkeypatch, email):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from jwt.algorithms import OKPAlgorithm

    from src.identity import better_auth
    from tests.conftest import AUTH_PUBLIC_JWK

    rotated = Ed25519PrivateKey.generate()
    rotated_jwk = {**json.loads(OKPAlgorithm.to_jwk(rotated.public_key())), "kid": "rotated"}
    published = [AUTH_PUBLIC_JWK]
    downloads = []

    class RotatingKeys(better_auth.JwksKeys):
        async def download(self):
            downloads.append(1)
            return {"keys": list(published)}

    keys = RotatingKeys()
    monkeypatch.setattr(better_auth, "jwks", keys)
    assert (await better_auth.verify_token(mint_token(email))).email == email
    assert (await better_auth.verify_token(mint_token(email))).email_verified is True
    assert len(downloads) == 1

    published.append(rotated_jwk)
    monkeypatch.setattr(better_auth, "REFRESH_INTERVAL_SECONDS", 0)
    identity = await better_auth.verify_token(mint_token(email, key=rotated, kid="rotated"))
    assert identity.id == f"ba-{email}"
    assert len(downloads) == 2


async def test_jwks_outage_maps_to_503(client, monkeypatch, email):
    from src.identity import better_auth

    class DownKeys(better_auth.JwksKeys):
        async def download(self):
            raise better_auth.AuthUnavailableError(better_auth.UNAVAILABLE)

    monkeypatch.setattr(better_auth, "jwks", DownKeys())
    r = await client.post("/api/auth/session", json={"accessToken": mint_token(email)})
    assert r.status_code == 503
    assert r.json() == {"error": {"message": "Sign-in is unavailable right now. Try again."}}


async def test_jwks_download_failures_are_unavailable(monkeypatch):
    import httpx
    import pytest

    from src.identity import better_auth

    original = httpx.AsyncClient

    def respond_with(handler):
        transport = httpx.MockTransport(handler)

        def client(*args, **kwargs):
            return original(*args, **{**kwargs, "transport": transport})

        monkeypatch.setattr(httpx, "AsyncClient", client)

    def down(request):
        raise httpx.ConnectError("refused", request=request)

    for handler in (
        lambda r: httpx.Response(502, text="bad gateway"),
        lambda r: httpx.Response(200, text="<html>"),
        down,
    ):
        respond_with(handler)
        with pytest.raises(better_auth.AuthUnavailableError):
            await better_auth.JwksKeys().download()

    respond_with(lambda r: httpx.Response(200, json={"keys": [{"kty": "nonsense", "kid": "x"}]}))
    keys = better_auth.JwksKeys()
    with pytest.raises(better_auth.AuthTokenError):
        await keys.get("x")


async def test_revoking_sessions_signs_out_every_device(client, email):
    from src.app import app

    await signup(client, email)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as other:
        await signup(other, email)
        assert (await other.get("/api/auth/me")).status_code == 200

        r = await client.post("/api/auth/sessions/revoke", json={"accessToken": mint_token(email)})
        assert r.status_code == 204

        assert (await client.get("/api/auth/me")).status_code == 401
        assert (await other.get("/api/auth/me")).status_code == 401


async def test_revoking_sessions_needs_a_valid_token(client, email):
    await signup(client, email)
    r = await client.post("/api/auth/sessions/revoke", json={"accessToken": "nope"})
    assert r.status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 200
