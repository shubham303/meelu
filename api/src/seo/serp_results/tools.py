from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.serp_results.schemas import SerpResults, SerpResultsRequest
from src.seo.serp_results.service import serp_results_service
from src.sites.service import site_service

DESK = "seo"


@tool(desk=DESK)
async def get_serp_results(
    keyword: str, use_cache: bool = False, location_code: int | None = None
) -> SerpResults:
    """The live Google top 10 for one keyword with each result's snippet, breadcrumb, date,
    rating, price and page and domain rank, plus a poisoning verdict: Google sometimes serves
    rank trackers fake results. When the verdict is poisoned, retry with a close variant of the
    keyword that keeps its meaning and intent; if the variants are poisoned too, say so and do
    not use vendor data for this keyword. Spends vendor credit unless use_cache reuses a
    results page from the last 7 days."""
    ctx = require_site()
    body = SerpResultsRequest(keyword=keyword, use_cache=use_cache, location_code=location_code)
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await serp_results_service.results(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), site, body
        )
