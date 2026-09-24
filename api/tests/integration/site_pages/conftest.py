import pytest

from tests.conftest import signup


@pytest.fixture(scope="session", autouse=True)
def mount_site_pages():
    from src.app import app
    from src.site_pages.endpoints import router

    mounted = any(getattr(r, "original_router", None) is router for r in app.routes)
    if not mounted:
        app.include_router(router, prefix="/api/v1")


@pytest.fixture
async def site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def save_page(client, **body):
    r = await client.post("/api/v1/site/pages", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def save_pages(client, items):
    r = await client.post("/api/v1/site/pages", json={"pages": items})
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def save_extraction(client, page_id, page_type):
    r = await client.post(
        "/api/v1/site/page-llm-extractions",
        json={"pageId": page_id, "pageType": page_type},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def list_pages(client, **params):
    r = await client.get("/api/v1/site/pages", params=params)
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def urls(client, **params):
    body = await list_pages(client, **params)
    return [p["url"] for p in body["pages"]]
