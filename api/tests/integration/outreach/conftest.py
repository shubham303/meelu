import pytest


def _ensure_router(app, path: str, router, prefix: str) -> None:
    if any(getattr(route, "path", None) == path for route in app.routes):
        return
    app.include_router(router, prefix=prefix)


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from src.app import app
    from src.outreach.endpoints import router as outreach_router

    _ensure_router(app, "/api/v1/outreach/projects", outreach_router, "/api/v1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def site(client, email):
    from tests.conftest import signup

    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "beans.example", "name": "Beans"})
    assert r.status_code == 201, r.text
    return r.json()["data"]
