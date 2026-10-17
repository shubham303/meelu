from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.seo.keyword_tracking.overview import months_back
from src.seo.market import markets
from src.seo.serp_history.constants import (
    CONSISTENT_SHARE,
    HISTORY_MONTHS,
    HISTORY_TTL,
    MAX_COMPETITORS,
    TOP_POSITIONS,
)
from src.seo.serp_history.presence import presence, snapshot_day
from src.seo.serp_history.schemas import SerpHistory, SerpHistoryRequest
from src.seo.site_seo.competitor_repository import site_competitors
from src.sites.schemas import SiteRecord


class SerpHistoryService:
    async def history(
        self, db: AsyncSession, caller: Caller, site: SiteRecord, body: SerpHistoryRequest
    ) -> SerpHistory:
        market = markets(site.markets, site.language, body.location_code)[0]
        saved = {c.domain for c in await site_competitors.list(db, site.id)}
        await db.commit()
        since = months_back(datetime.now(UTC).date(), HISTORY_MONTHS)[0]
        snapshots = await seo_data.historical_serps(
            caller, body.keyword, market, since.isoformat(), ttl=HISTORY_TTL
        )
        competitors, sporadic, ours = presence(
            snapshots, site.domain, TOP_POSITIONS, CONSISTENT_SHARE, saved
        )
        days = [d for d in (snapshot_day(s) for s in snapshots) if d]
        return SerpHistory(
            keyword=body.keyword,
            location_code=market["location_code"],
            language_code=market["language_code"],
            snapshots=len(snapshots),
            first_day=min(days) if days else None,
            last_day=max(days) if days else None,
            top_positions=TOP_POSITIONS,
            consistent_share=CONSISTENT_SHARE,
            competitors=competitors[:MAX_COMPETITORS],
            sporadic=sporadic + max(len(competitors) - MAX_COMPETITORS, 0),
            ours=ours,
        )


serp_history_service = SerpHistoryService()
