from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.prospect_sources.apify import ApifyProspectAdapter
from src.providers.prospect_sources.free import FreeProspectAdapter
from src.providers.prospect_sources.sources import SOURCES
from src.providers.registry import Caller, ProviderFacade

TTL = timedelta(hours=24)


class ProspectSourcesProvider(ProviderFacade):
    domain = "prospect-sources"
    label = "prospect sourcing"

    def available_sources(self) -> list[dict]:
        return [
            {
                "id": s["id"],
                "label": s["label"],
                "access": s["access"],
                "available": self.supports(f"prospects.{s['id']}"),
            }
            for s in SOURCES
        ]

    async def search_source(
        self, db: AsyncSession, caller: Caller, source: str, queries: list[str], limit: int = 20
    ) -> list[dict]:
        query = {"queries": queries, "limit": limit}
        return await self.fetch(
            db,
            caller,
            f"prospects.{source}",
            {"source": source, **query},
            lambda a: a.search_prospects(source, query),
            TTL,
        )


prospect_sources = ProspectSourcesProvider([FreeProspectAdapter(), ApifyProspectAdapter()])
