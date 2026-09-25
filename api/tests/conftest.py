import asyncio
import os
import sys
import uuid
from pathlib import Path

import psycopg
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
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s",
            (TEST_DB_NAME,),
        )
        conn.execute(f'drop database if exists "{TEST_DB_NAME}"')


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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def email():
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


async def signup(client, email, password="secret123", name="Test User"):
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": password, "name": name}
    )
    assert r.status_code == 201, r.text
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 204, r.text
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
