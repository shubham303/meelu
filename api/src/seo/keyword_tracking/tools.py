from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.keyword_tracking.schemas import TrackKeywordsRequest, VolumesTracked
from src.seo.keyword_tracking.service import keyword_tracking_service
from src.seo.market import site_markets

DESK = "seo"


@tool(writes=True, desk=DESK)
async def track_keyword_volumes(
    keywords: list[str], location_code: int | None = None
) -> VolumesTracked:
    """Record the monthly search volume history (Google Ads and clickstream) of these
    keywords in `seo_volume_history`, per market of the site unless one location_code is
    passed. Query the table with SQL afterwards. Spends vendor credit."""
    ctx = require_site()
    body = TrackKeywordsRequest(keywords=keywords)
    async with unit_of_work() as db:
        targets = await site_markets(db, ctx.user_id, ctx.site_id, location_code)
        return await keyword_tracking_service.track_volumes(
            db,
            Caller(user_id=ctx.user_id, site_id=ctx.site_id),
            ctx.user_id,
            ctx.site_id,
            body,
            targets,
        )
