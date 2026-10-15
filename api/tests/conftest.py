import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

import psycopg
import psycopg.sql
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_DB_NAME = os.environ.get("MEELU_TEST_DB") or f"meelu_api_test_{os.getpid()}"


def _env_value(name: str) -> str:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"{name} not found in api/.env")


def _on_test_database(url: str) -> str:
    return url.rsplit("/", 1)[0] + "/" + TEST_DB_NAME


def _plain(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


BASE_URL = _env_value("DATABASE_URL")
MIGRATE_BASE_URL = _env_value("MIGRATE_DATABASE_URL")
TEST_URL = _on_test_database(BASE_URL)
MIGRATE_TEST_URL = _on_test_database(MIGRATE_BASE_URL)

os.environ["DATABASE_URL"] = TEST_URL
os.environ["MIGRATE_DATABASE_URL"] = MIGRATE_TEST_URL


@pytest.fixture(scope="session", autouse=True)
def test_database():
    with psycopg.connect(_plain(MIGRATE_BASE_URL), autocommit=True) as conn:
        exists = conn.execute(
            "select 1 from pg_database where datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(f'create database "{TEST_DB_NAME}"')

    yield

    if os.environ.get("MEELU_TEST_DB"):
        return
    with psycopg.connect(_plain(MIGRATE_TEST_URL)) as conn:
        tenant_roles = [row[0] for row in conn.execute("select role_name from agent_tenants")]
    with psycopg.connect(_plain(MIGRATE_BASE_URL), autocommit=True) as conn:
        conn.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s",
            (TEST_DB_NAME,),
        )
        conn.execute(f'drop database if exists "{TEST_DB_NAME}"')
        for role in tenant_roles:
            conn.execute(
                psycopg.sql.SQL("drop role if exists {}").format(psycopg.sql.Identifier(role))
            )


@pytest.fixture(scope="session", autouse=True)
def schema(test_database):
    from sqlalchemy import text as sql_text
    from sqlalchemy.ext.asyncio import create_async_engine

    import src.core.tables  # noqa: F401
    from src.core.db_roles import grant_app_role
    from src.core.orm import Base

    async def build():
        engine = create_async_engine(MIGRATE_TEST_URL)
        async with engine.begin() as conn:
            await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(build())
    grant_app_role(MIGRATE_TEST_URL, TEST_URL)


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from src.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c


@pytest.fixture
def email():
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


AUTH_ORIGIN = "https://ui.test"
AUTH_KID = "test-key"


def _auth_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from jwt.algorithms import OKPAlgorithm

    private = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public = json.loads(OKPAlgorithm.to_jwk(private.public_key()))
    return private, {**public, "kid": AUTH_KID, "alg": "EdDSA"}


AUTH_PRIVATE_KEY, AUTH_PUBLIC_JWK = _auth_keypair()


def mint_token(email, name="Test User", verified=True, key=None, kid=AUTH_KID, **claims):
    import time

    import jwt

    now = int(time.time())
    payload = {
        "sub": f"ba-{email}",
        "email": email,
        "emailVerified": verified,
        "name": name,
        "iss": AUTH_ORIGIN,
        "aud": AUTH_ORIGIN,
        "iat": now,
        "exp": now + 300,
        **claims,
    }
    return jwt.encode(payload, key or AUTH_PRIVATE_KEY, algorithm="EdDSA", headers={"kid": kid})


@pytest.fixture(autouse=True)
def better_auth_keys(monkeypatch):
    from src.identity import better_auth
    from src.settings import settings

    class TestKeys(better_auth.JwksKeys):
        async def download(self):
            return {"keys": [AUTH_PUBLIC_JWK]}

    monkeypatch.setattr(settings, "auth_jwks_url", f"{AUTH_ORIGIN}/auth/jwks")
    monkeypatch.setattr(settings, "auth_issuer", AUTH_ORIGIN)
    monkeypatch.setattr(settings, "auth_audience", AUTH_ORIGIN)
    monkeypatch.setattr(better_auth, "jwks", TestKeys())


async def signup(client, email, name="Test User", credits=1.0, trial=False):
    r = await client.post("/api/auth/session", json={"accessToken": mint_token(email, name)})
    assert r.status_code == 200, r.text
    from sqlalchemy import text

    from src.core.database import unit_of_work
    from src.credits.ledger import credit_ledger_service

    async with unit_of_work() as db:
        user_id = (
            await db.execute(text('SELECT id FROM "user" WHERE email = :e'), {"e": email})
        ).scalar_one()
        if not trial:
            await db.execute(
                text("UPDATE \"user\" SET created_at = now() - interval '30 days' WHERE id = :u"),
                {"u": user_id},
            )
        if credits:
            await credit_ledger_service.apply(
                db, user_id, round(credits * 1_000_000), "grant", "Test credits"
            )
    return r


@pytest.fixture
def screener(monkeypatch):
    from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter
    from src.providers.json_data_extractor.service import json_data_extractor
    from src.providers.registry import VendorResponse

    class YesScreener(JsonDataExtractorAdapter):
        id = "fake-screener"
        name = "Fake screener"
        capabilities = frozenset({DECIDE})
        charges = False

        async def decide(self, state, questions):
            return VendorResponse(
                {
                    "model": "fake",
                    "answers": {
                        key: {
                            "type": "choice",
                            "choice": "yes",
                            "probabilities": {"yes": 0.9, "no": 0.1},
                            "confidence": 0.9,
                        }
                        for key in questions
                    },
                }
            )

    fake = YesScreener()
    monkeypatch.setattr(json_data_extractor, "adapters", [fake])
    return fake
