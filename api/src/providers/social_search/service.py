from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.registry import Caller, ProviderFacade
from src.providers.social_search.apify import ApifySocialAdapter
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
        db: AsyncSession,
        caller: Caller,
        platform: str,
        keywords: list[str],
        since: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        query = {"keywords": keywords, "since": since, "limit": limit}
        return await self.fetch(
            db,
            caller,
            f"search.{platform}",
            {
                "platform": platform,
                "keywords": keywords,
                "since": (since or "")[:10],
                "limit": limit,
            },
            lambda a: a.search_posts(platform, query),
            TTL,
        )


social_search = SocialSearchProvider([MeeluPublicAdapter(), ApifySocialAdapter()])
