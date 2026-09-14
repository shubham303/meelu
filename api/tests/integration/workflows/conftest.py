import pytest


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient
    from src.workflows.endpoints import router as workflows_router

    from src.app import app

    if not any(getattr(r, "path", "") == "/api/v1/workflows/runs" for r in app.routes):
        app.include_router(workflows_router, prefix="/api/v1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
