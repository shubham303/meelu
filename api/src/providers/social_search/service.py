from datetime import timedelta

from src.providers.registry import Caller, ProviderFacade
from src.providers.social_search.apify import apify_adapters
from src.providers.social_search.meelu_public import MeeluPublicAdapter
from src.providers.social_search.platforms import PLATFORMS

TTL = timedelta(hours=6)


class SocialSearchProvider(ProviderFacade):
    domain = "social-listening"
    label = "social listening"

    def available_platforms(self) -> list[dict]:
        return [
            {
                "id": p["id"],
                "label": p["label"],
                "access": p["access"],
                "available": self.supports(f"search.{p['id']}"),
            }
            for p in PLATFORMS
        ]

    async def search_platform(
        self,
        caller: Caller,
        platform: str,
        keywords: list[str],
        since: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        query = {"keywords": keywords, "since": since, "limit": limit}
        return await self.fetch(
            caller,
            f"search.{platform}",
            lambda a: a.vendor_query(platform, query),
            lambda a: a.search_posts(platform, query),
            TTL,
        )


social_search = SocialSearchProvider([MeeluPublicAdapter(), *apify_adapters()])
