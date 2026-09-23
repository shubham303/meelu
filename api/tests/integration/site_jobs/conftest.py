from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import signup


def _mount() -> None:
    from src.app import app
    from src.crawl_jobs.endpoints import router as crawl_router

    mounted = {getattr(route, "path", "") for route in app.routes}
    if "/api/v1/site/crawl-jobs" not in mounted:
        app.include_router(crawl_router, prefix="/api/v1")


@pytest.fixture(autouse=True)
def job_routes():
    _mount()


@pytest.fixture
async def site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "jobs.example.com", "name": "Jobs"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def add_page(site_id, user_id_from, url, **fields):
    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage

    now = datetime.now(UTC)
    async with unit_of_work() as db:
        page = SitePage(
            id=uid("pg"),
            user_id=user_id_from,
            site_id=site_id,
            url=url,
            created_at=now,
            updated_at=now,
            **fields,
        )
        db.add(page)
        await db.flush()
        return page.id


async def site_owner(site_id):
    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.sites.models.site import Site

    async with unit_of_work() as db:
        return (await db.execute(select(Site.user_id).where(Site.id == site_id))).scalar_one()


async def backdate_heartbeat(job_id, minutes):
    from sqlalchemy import update

    from src.core.database import unit_of_work
    from src.crawl_jobs.models.site_crawl_job import SiteCrawlJob

    stale = datetime.now(UTC) - timedelta(minutes=minutes)
    async with unit_of_work() as db:
        await db.execute(
            update(SiteCrawlJob)
            .where(SiteCrawlJob.id == job_id)
            .values(heartbeat_at=stale, started_at=stale, created_at=stale)
        )
