from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.seo.keyword_tracking.constants import HISTORY_MONTHS
from src.seo.keyword_tracking.overview import months_back, stats, tracked_keywords
from src.seo.keyword_tracking.repositories.volumes import seo_volume_history
from src.seo.keyword_tracking.schemas import (
    Market,
    TrackedOverview,
    TrackKeywordsRequest,
    VolumeRow,
    VolumesTracked,
)
from src.seo.keyword_tracking.shape import volume_rows
from src.seo.market import country_of, markets
from src.seo.site_search.repositories.site_search_daily import site_search_dailies
from src.sites.schemas import SiteRecord


class KeywordTrackingService:
    async def overview(
        self, db: AsyncSession, site: SiteRecord, location_code: int | None
    ) -> TrackedOverview:
        own = markets(site.markets, site.language)
        stored = set(await seo_volume_history.markets(db, site.id))
        known = list(
            dict.fromkeys([(m["location_code"], m["language_code"]) for m in own] + sorted(stored))
        )
        chosen = next((m for m in known if m[0] == location_code), known[0])
        today = datetime.now(UTC).date()
        months = months_back(today, HISTORY_MONTHS)
        volumes = await seo_volume_history.months(db, site.id, *chosen, months[0])
        positions = await site_search_dailies.monthly_positions(
            db,
            site.id,
            sorted({keyword for keyword, _, _ in volumes}),
            country_of(chosen[0]) or "",
            months[0],
        )
        rows = tracked_keywords(months, positions, volumes)
        return TrackedOverview(
            location_code=chosen[0],
            language_code=chosen[1],
            markets=[
                Market(location_code=c, language_code=lang, country=country_of(c))
                for c, lang in known
            ],
            months=months,
            stats=stats(rows),
            keywords=rows,
        )

    async def track_volumes(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site_id: str,
        body: TrackKeywordsRequest,
        targets: list[dict],
    ) -> VolumesTracked:
        rows: list[VolumeRow] = []
        await db.commit()
        for market in targets:
            for item in await seo_data.keyword_overview(caller, body.keywords, market):
                rows += volume_rows(item, market)
        merged = [r for r in rows if r.keyword]
        saved = await seo_volume_history.upsert_many(db, user_id, site_id, merged)
        found = {r.keyword for r in merged}
        return VolumesTracked(
            keywords=len(body.keywords),
            months=len({r.month for r in merged}),
            rows=saved,
            without_data=[k for k in body.keywords if k not in found],
        )


keyword_tracking_service = KeywordTrackingService()
