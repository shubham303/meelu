from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.pagination import PaginationParams
from src.providers.registry import Caller
from src.seo.site_seo.schemas import (
    BacklinkDomainRemoved,
    BacklinkDomainRequest,
    BacklinkOpportunity,
    BacklinksFetched,
    CompetitorsChange,
    DomainsRequest,
    OpportunitiesDismissed,
)
from src.seo.site_seo.service import site_seo_service

DESK = "seo"


def caller() -> Caller:
    ctx = require_site()
    return Caller(user_id=ctx.user_id, site_id=ctx.site_id)


@tool(writes=True, desk=DESK)
async def add_competitors(domains: list[str]) -> CompetitorsChange:
    """Save domains as this website's competitors with their domain rank. Saved domains are
    left as they are; backlinks are not fetched. Spends a little vendor credit."""
    ctx = require_site()
    body = DomainsRequest(domains=domains)
    async with unit_of_work() as db:
        return await site_seo_service.add_competitors(
            db, caller(), ctx.user_id, ctx.site_id, ctx.site_domain, body.domains
        )


@tool(writes=True, desk=DESK)
async def fetch_competitor_backlinks(domains: list[str]) -> BacklinksFetched:
    """Fetch the genuine backlinks of these saved competitors into `site_backlinks`, replacing
    earlier ones, plus this website's own the first time. Only for the competitors the user
    names; it spends vendor credit per domain."""
    ctx = require_site()
    body = DomainsRequest(domains=domains)
    async with unit_of_work() as db:
        return await site_seo_service.fetch_backlinks(
            db, caller(), ctx.user_id, ctx.site_id, ctx.site_domain, body.domains
        )


@tool(writes=True, desk=DESK)
async def remove_competitors(domains: list[str]) -> CompetitorsChange:
    """Remove saved competitors that do not belong, with the backlinks fetched for them.
    Only when the user asks."""
    ctx = require_site()
    body = DomainsRequest(domains=domains)
    async with unit_of_work() as db:
        return await site_seo_service.remove_competitors(db, ctx.site_id, body.domains)


@tool(desk=DESK)
async def list_backlink_opportunities(
    page: int = 1, page_size: int = 50
) -> list[BacklinkOpportunity]:
    """Domains linking to saved competitors but not to this website and not dismissed, most competitors linked first, the same list the Backlinks screen shows.
    At most 100 per page."""
    ctx = require_site()
    async with unit_of_work() as db:
        found = await site_seo_service.opportunities(
            db, ctx.site_id, ctx.site_domain, PaginationParams(page=page, page_size=page_size)
        )
    return found.data


@tool(writes=True, desk=DESK)
async def dismiss_backlink_opportunities(domains: list[str]) -> OpportunitiesDismissed:
    """Hide linking domains from the backlink opportunities for good, even after their
    backlinks are fetched again. Only when the user asks."""
    ctx = require_site()
    body = DomainsRequest(domains=domains)
    async with unit_of_work() as db:
        return await site_seo_service.dismiss_opportunities(db, ctx.site_id, body.domains)


@tool(writes=True, desk=DESK)
async def remove_backlink_domain(domain: str) -> BacklinkDomainRemoved:
    """Delete every stored backlink from one linking domain, to competitors and to this
    website. It comes back if those backlinks are fetched again; dismiss it to keep it out of
    the opportunities for good. Only when the user asks."""
    ctx = require_site()
    body = BacklinkDomainRequest(domain=domain)
    async with unit_of_work() as db:
        return await site_seo_service.remove_backlink_domain(db, ctx.site_id, body.domain)
