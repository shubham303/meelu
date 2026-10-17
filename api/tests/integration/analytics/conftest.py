import pytest


@pytest.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from src.analytics.endpoints import router as analytics_router
    from src.app import app

    if not any(getattr(r, "path", "") == "/api/v1/analytics/chats" for r in app.routes):
        app.include_router(analytics_router, prefix="/api/v1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c
