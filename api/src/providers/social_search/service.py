from src.providers.errors import ProviderRequestError
from src.providers.registry import Caller, ProviderFacade
from src.providers.social_search.meelu_public import MeeluPublicAdapter
from src.providers.social_search.platforms import PLATFORMS


class SocialSearchProvider(ProviderFacade):
    domain = "social-listening"
    label = "social listening"

    def available_platforms(self) -> list[dict]:
        return [
            {
                "id": p["id"],
                "label": p["label"],
                "access": p["access"],
                "available": p["access"] == "web" or self.supports(f"search.{p['id']}"),
            }
            for p in PLATFORMS
        ]

    async def search_platform(
        self,
        caller: Caller,
        platform: str,
        keywords: list[str],
        since: str | None,
        per_keyword: int,
    ) -> dict:
        query = {"keywords": keywords, "since": since, "per_keyword": per_keyword}
        return await self.fetch(
            caller,
            f"search.{platform}",
            lambda a: a.vendor_query(platform, query),
            lambda a: a.search_posts(platform, query),
            None,
        )

    async def max_cost_micros(
        self, platform: str, keyword_count: int, per_keyword: int
    ) -> int | None:
        if keyword_count == 0:
            return 0
        adapters = self.adapters_for(f"search.{platform}")
        if not adapters:
            return None
        try:
            return await adapters[0].max_cost_micros(keyword_count, per_keyword)
        except ProviderRequestError:
            return None


social_search = SocialSearchProvider([MeeluPublicAdapter()])
