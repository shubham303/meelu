from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.market import site_markets
from src.seo.site_seo.constants import (
    DEFAULT_COMPETITORS,
    DEFAULT_OPPORTUNITIES,
    MAX_COMPETITORS,
    MAX_OPPORTUNITIES,
    SeoList,
)
from src.seo.site_seo.schemas import (
    BacklinkOpportunities,
    FoundCompetitors,
    SeoListChange,
    SeoListItemsRequest,
)
from src.seo.site_seo.service import site_seo_service

DESK = "seo"


def clamp(limit: int, cap: int) -> int:
    return min(max(int(limit), 1), cap)


def caller() -> Caller:
    ctx = require_site()
    return Caller(user_id=ctx.user_id, site_id=ctx.site_id)


@tool(desk=DESK)
async def find_competitors(
    limit: int = DEFAULT_COMPETITORS,
    location_code: int | None = None,
) -> FoundCompetitors:
    """Domains competing with this website in search: those sharing its ranked keywords and
    those winning the results pages of its top Search Console queries, across the site's
    markets unless one location_code is passed. Marks the ones already saved. Spends vendor
    credit."""
    ctx = require_site()
    async with unit_of_work() as db:
        targets = await site_markets(db, ctx.user_id, ctx.site_id, location_code)
        return await site_seo_service.find_competitors(
            db, caller(), ctx.site_id, ctx.site_domain, clamp(limit, MAX_COMPETITORS), targets
        )


@tool(desk=DESK)
async def find_backlink_opportunities(
    competitors: list[str] | None = None,
    limit: int = DEFAULT_OPPORTUNITIES,
) -> BacklinkOpportunities:
    """Domains linking to competitors but not to this website, most competitors first.
    Uses the saved competitors unless some are passed. Spends vendor credit."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await site_seo_service.find_backlink_opportunities(
            db, caller(), ctx.site_id, ctx.site_domain, competitors, clamp(limit, MAX_OPPORTUNITIES)
        )


@tool(writes=True, desk=DESK)
async def add_to_seo_list(list: SeoList, items: list[str]) -> SeoListChange:
    """Add domains to one of this website's saved SEO lists. Entries already there are
    left as they are."""
    ctx = require_site()
    body = SeoListItemsRequest(items=items)
    async with unit_of_work() as db:
        return await site_seo_service.add_items(db, ctx.user_id, ctx.site_id, list, body.items)


@tool(writes=True, desk=DESK)
async def remove_from_seo_list(list: SeoList, items: list[str]) -> SeoListChange:
    """Remove domains that do not belong from one of this website's saved SEO lists."""
    ctx = require_site()
    body = SeoListItemsRequest(items=items)
    async with unit_of_work() as db:
        return await site_seo_service.remove_items(db, ctx.user_id, ctx.site_id, list, body.items)
