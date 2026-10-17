from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.seo.keyword_clusters.constants import SERP_DEPTH, SERP_DEVICE
from src.seo.keyword_clusters.repository import seo_keyword_clusters
from src.seo.market import markets
from src.seo.serp_results.constants import MAX_SIBLINGS, SERP_TTL, TOP_POSITIONS
from src.seo.serp_results.poisoning import message_for, organic, rated, sibling_check, verdict
from src.seo.serp_results.schemas import SerpPull, SerpResults, SerpResultsRequest
from src.sites.schemas import SiteRecord


class SerpResultsService:
    async def results(
        self, db: AsyncSession, caller: Caller, site: SiteRecord, body: SerpResultsRequest
    ) -> SerpResults:
        market = markets(site.markets, site.language, body.location_code)[0]
        return await self.check(db, caller, site, body.keyword, market, refresh=not body.use_cache)

    async def check(
        self,
        db: AsyncSession,
        caller: Caller,
        site: SiteRecord,
        keyword: str,
        market: dict,
        refresh: bool,
    ) -> SerpResults:
        pulled = await self.pull(db, caller, site, keyword, market, refresh)
        ranks = await seo_data.pages_summary(caller, [r["url"] for r in pulled.main])
        return self.judge(pulled, ranks, site.domain)

    async def pull(
        self,
        db: AsyncSession,
        caller: Caller,
        site: SiteRecord,
        keyword: str,
        market: dict,
        refresh: bool,
    ) -> SerpPull:
        cluster = await seo_keyword_clusters.containing(
            db, site.id, keyword, market["location_code"], market["language_code"]
        )
        await db.commit()
        siblings = (
            [k for k in dict.fromkeys([cluster.main_keyword, *cluster.keywords]) if k != keyword][
                :MAX_SIBLINGS
            ]
            if cluster
            else []
        )

        async def top(phrase: str) -> tuple[dict | None, list[dict]]:
            serp = await seo_data.serp_organic(
                caller,
                phrase,
                SERP_DEVICE,
                SERP_DEPTH,
                market,
                ttl=SERP_TTL,
                refresh=refresh,
            )
            return serp, organic(serp, TOP_POSITIONS)

        serp, main = await top(keyword)
        checks = [sibling_check(k, main, (await top(k))[1]) for k in siblings]
        return SerpPull(keyword=keyword, market=market, serp=serp, main=main, siblings=checks)

    def judge(self, pulled: SerpPull, ranks: dict[str, dict], site_domain: str) -> SerpResults:
        results = rated(pulled.main, ranks, site_domain)
        found, weak_top, overlap, reasons = verdict(results, pulled.siblings)
        return SerpResults(
            keyword=pulled.keyword,
            location_code=pulled.market["location_code"],
            language_code=pulled.market["language_code"],
            checked_at=(pulled.serp or {}).get("datetime"),
            results=results,
            weak_top=weak_top,
            siblings=pulled.siblings,
            sibling_overlap=overlap,
            verdict=found,
            reasons=reasons,
            message=message_for(found),
        )


serp_results_service = SerpResultsService()
