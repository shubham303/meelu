import pytest

from src.app import app
from src.content.endpoints import router as content_router
from tests.conftest import signup

if not any(getattr(route, "path", "").startswith("/api/v1/content") for route in app.routes):
    app.include_router(content_router, prefix="/api/v1")


@pytest.fixture
async def workspace(client, email):
    await signup(client, email)
    r = await client.post(
        "/api/v1/sites", json={"domain": "coffee.example.com", "name": "Coffee Gear"}
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def make_piece(client, **overrides):
    body = {"title": "Untitled piece", **overrides}
    r = await client.post("/api/v1/content/pieces", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]
