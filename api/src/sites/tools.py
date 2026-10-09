from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.sites.schemas import SiteResponse, SiteUpdateRequest
from src.sites.service import site_service


@tool(writes=True, desk="site")
async def save_site_market(markets: list[str], language: str | None = None) -> SiteResponse:
    """Save the countries this website sells to (two-letter codes such as US or GB) and the
    language its searchers use (such as en). Only what the user confirmed."""
    ctx = require_site()
    body = SiteUpdateRequest(markets=markets, language=language)
    async with unit_of_work() as db:
        site = await site_service.update_as_agent(db, ctx.user_id, ctx.site_id, body)
    return SiteResponse.model_validate(site)
