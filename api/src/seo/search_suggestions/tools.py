from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.search_suggestions.schemas import SearchSuggestions, SearchSuggestionsRequest
from src.seo.search_suggestions.service import search_suggestions_service
from src.sites.service import site_service

DESK = "seo"


@tool(desk=DESK)
async def get_search_suggestions(
    keywords: list[str], use_cache: bool = False, location_code: int | None = None
) -> list[SearchSuggestions]:
    """What Google suggests around each keyword (at most 10): its autocomplete completions,
    and the People Also Ask questions and related searches on its results page, one result
    per keyword. Spends vendor credit unless use_cache reuses answers from the last 7 days."""
    ctx = require_site()
    body = SearchSuggestionsRequest(
        keywords=keywords, use_cache=use_cache, location_code=location_code
    )
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await search_suggestions_service.suggestions(
        Caller(user_id=ctx.user_id, site_id=ctx.site_id), site, body
    )
