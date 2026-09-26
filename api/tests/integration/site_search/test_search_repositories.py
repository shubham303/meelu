import pytest
from sqlalchemy import select

from src.core.database import unit_of_work
from src.site_pages.models.site_page import SitePage
from src.site_search.repositories.site_page_index_status import site_page_index_statuses
from src.site_search.repositories.site_search_daily import site_search_dailies
from src.site_search.schemas import NewSitePageIndexStatus
from tests.conftest import signup
from tests.integration.site_search.test_search_data import (
    BATCH,
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


async def test_seo_window_totals(client, email):
    site = await _site(client, email)
    r = await client.post("/api/v1/site/search-data/rows", json=BATCH)
    assert r.status_code == 200, r.text

    async with unit_of_work() as db:
        pages = {p.page: p for p in await site_search_dailies.page_window_totals(db, site["id"])}
        scoped = await site_search_dailies.page_window_totals(db, site["id"], [BLOG])
        queries = {
            q.query: q for q in await site_search_dailies.query_window_totals(db, site["id"])
        }
        pairs = {
            (p.query, p.page): p
            for p in await site_search_dailies.query_page_window_totals(db, site["id"])
        }
        old = await site_search_dailies.has_data_older_than(db, site["id"], 365)
        recent = await site_search_dailies.has_data_older_than(db, site["id"], 3)

    assert pages[PRICING].impressions_28d == 350
    assert pages[PRICING].clicks_28d == 35
    assert pages[PRICING].impressions_ly_28d is None
    assert [p.page for p in scoped] == [BLOG]
    assert queries["espresso machine"].impressions_28d == 320
    assert queries["espresso machine"].clicks_28d == 32
    assert queries["coffee grinder"].impressions_prev_28d == 0
    pricing = pairs[("espresso machine", PRICING)]
    assert pricing.impressions_28d == 300
    assert pricing.position_28d == pytest.approx((100 * 5 + 200 * 4) / 300)
    assert pricing.impressions_90d == 300
    assert pricing.leader_days_90d == 2
    assert pairs[("espresso machine", BLOG)].leader_days_90d == 0
    assert old is False
    assert recent is True


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
