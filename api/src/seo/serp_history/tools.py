from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.serp_history.schemas import SerpHistory, SerpHistoryRequest
from src.seo.serp_history.service import serp_history_service
from src.sites.service import site_service

DESK = "seo"


@tool(desk=DESK)
async def keyword_serp_history(keyword: str, location_code: int | None = None) -> SerpHistory:
    """The domains that held a top-10 organic result for this keyword in at least half of
    the last twelve months of results-page snapshots, most consistent first, with this
    website's own presence. Domains seen less often are only counted. Covers the site's
    first market unless one location_code is passed. Spends vendor credit."""
    ctx = require_site()
    body = SerpHistoryRequest(keyword=keyword, location_code=location_code)
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await serp_history_service.history(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), site, body
        )
