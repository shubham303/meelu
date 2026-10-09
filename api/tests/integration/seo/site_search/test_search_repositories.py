from sqlalchemy import select

from src.core.database import unit_of_work
from src.seo.site_search.repositories.site_page_index_status import site_page_index_statuses
from src.seo.site_search.schemas import NewSitePageIndexStatus
from src.site_pages.models.site_page import SitePage
from tests.conftest import signup
from tests.integration.seo.site_search.test_search_data import (
    BLOG,
    PRICING,
    make_site,
    seed_page,
)


async def _site(client, email):
    await signup(client, email)
    site = await make_site(client)
    me = (await client.get("/api/auth/me")).json()["data"]
    return {**site, "userId": me["id"]}


async def test_index_status_by_page_ids(client, email):
    site = await _site(client, email)
    await seed_page(site, PRICING)
    await seed_page(site, BLOG)

    async with unit_of_work() as db:
        ids = {
            p.url: p.id
            for p in (
                await db.execute(select(SitePage).where(SitePage.site_id == site["id"]))
            ).scalars()
        }
        applied = await site_page_index_statuses.upsert_many(
            db,
            site["userId"],
            site["id"],
            {
                ids[PRICING]: NewSitePageIndexStatus(
                    url=PRICING,
                    index_state="indexed",
                    coverage_state="Submitted and indexed",
                    last_crawl_time="2026-08-01T10:00:00Z",
                )
            },
        )
        again = await site_page_index_statuses.upsert_many(
            db,
            site["userId"],
            site["id"],
            {ids[PRICING]: NewSitePageIndexStatus(url=PRICING, index_state="excluded")},
        )
        rows = await site_page_index_statuses.list_by_page_ids(
            db, site["id"], [ids[PRICING], ids[BLOG]]
        )

    assert applied == 1
    assert again == 1
    assert len(rows) == 1
    assert rows[0].page_id == ids[PRICING]
    assert rows[0].index_state == "excluded"
    assert rows[0].index_checked_at is not None
