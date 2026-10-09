import asyncio
import os
import sys
import uuid
from pathlib import Path

import psycopg
import psycopg.sql
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_DB_NAME = os.environ.get("MEELU_TEST_DB") or f"meelu_api_test_{os.getpid()}"


def _base_database_url() -> str:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL not found in api/.env")


BASE_URL = _base_database_url()
TEST_URL = BASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB_NAME
ADMIN_URL = BASE_URL.replace("postgresql+psycopg://", "postgresql://")

os.environ["DATABASE_URL"] = TEST_URL


@pytest.fixture(scope="session", autouse=True)
def test_database():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        exists = conn.execute(
            "select 1 from pg_database where datname = %s", (TEST_DB_NAME,)
        ).fetchone()
        if not exists:
            conn.execute(f'create database "{TEST_DB_NAME}"')

    yield

    if os.environ.get("MEELU_TEST_DB"):
        return
    with psycopg.connect(TEST_URL.replace("postgresql+psycopg://", "postgresql://")) as conn:
        tenant_roles = [row[0] for row in conn.execute("select role_name from agent_tenants")]
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
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

    import src.core.tables  # noqa: F401
    from src.core.database import engine
    from src.core.orm import Base

    async def build():
        async with engine.begin() as conn:
            await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(build())


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from src.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c


@pytest.fixture
def email():
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(autouse=True)
def fake_supabase(monkeypatch):
    from src.identity import supabase

    async def fetch_user(access_token: str) -> supabase.SupabaseUser:
        kind, _, rest = access_token.partition("|")
        if kind != "test":
            raise supabase.SupabaseAuthError("The sign-in token is invalid or expired.")
        email, _, name = rest.partition("|")
        return supabase.SupabaseUser(
            id=f"sb-{email}", email=email, name=name, image=None, email_confirmed=True
        )

    monkeypatch.setattr(supabase, "fetch_user", fetch_user)


async def signup(client, email, name="Test User"):
    r = await client.post("/api/auth/session", json={"accessToken": f"test|{email}|{name}"})
    assert r.status_code == 200, r.text
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
