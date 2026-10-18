from datetime import timedelta

from src.providers.people_search.apify import apify_people_adapters
from src.providers.registry import Caller, ProviderFacade

SEARCH_TTL = timedelta(days=7)
ACTIVITY_TTL = timedelta(days=1)


class PeopleSearchProvider(ProviderFacade):
    domain = "people-search"
    label = "people search"

    async def search_linkedin(
        self,
        caller: Caller,
        query: str,
        titles: list[str],
        locations: list[str],
        limit: int,
        page: int = 1,
    ) -> list[dict]:
        request = {
            "page": page,
            "query": query.strip(),
            "titles": sorted({t.strip() for t in titles if t.strip()}),
            "locations": sorted({loc.strip() for loc in locations if loc.strip()}),
            "limit": limit,
        }
        return await self.fetch(
            caller,
            "search.linkedin",
            lambda a: a.vendor_query("search.linkedin", request),
            lambda a: a.search_people(request),
            SEARCH_TTL,
        )

    async def activity(
        self, caller: Caller, platform: str, people: list[str], per_person: int
    ) -> dict[str, list[dict]]:
        request = {"people": sorted(set(people)), "per_person": per_person}
        return await self.fetch(
            caller,
            f"activity.{platform}",
            lambda a: a.vendor_query(f"activity.{platform}", request),
            lambda a: a.activity(platform, request),
            ACTIVITY_TTL,
        )


people_search = PeopleSearchProvider(apify_people_adapters())
