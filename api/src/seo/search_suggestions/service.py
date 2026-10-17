import asyncio

from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.seo.keyword_clusters.constants import SERP_DEPTH, SERP_DEVICE
from src.seo.market import markets
from src.seo.search_suggestions.constants import SUGGESTIONS_TTL
from src.seo.search_suggestions.extract import autocomplete, people_also_ask, related_searches
from src.seo.search_suggestions.schemas import SearchSuggestions, SearchSuggestionsRequest
from src.seo.serp_results.constants import SERP_TTL
from src.sites.schemas import SiteRecord


class SearchSuggestionsService:
    async def suggestions(
        self, caller: Caller, site: SiteRecord, body: SearchSuggestionsRequest
    ) -> list[SearchSuggestions]:
        market = markets(site.markets, site.language, body.location_code)[0]
        refresh = not body.use_cache
        return list(
            await asyncio.gather(
                *(self._one(caller, keyword, market, refresh) for keyword in body.keywords)
            )
        )

    async def _one(
        self, caller: Caller, keyword: str, market: dict, refresh: bool
    ) -> SearchSuggestions:
        typed = await seo_data.serp_autocomplete(
            caller, keyword, market, ttl=SUGGESTIONS_TTL, refresh=refresh
        )
        serp = await seo_data.serp_organic(
            caller, keyword, SERP_DEVICE, SERP_DEPTH, market, ttl=SERP_TTL, refresh=refresh
        )
        return SearchSuggestions(
            keyword=keyword,
            location_code=market["location_code"],
            language_code=market["language_code"],
            autocomplete=autocomplete(typed, keyword),
            people_also_ask=people_also_ask(serp),
            related_searches=related_searches(serp),
        )


search_suggestions_service = SearchSuggestionsService()
