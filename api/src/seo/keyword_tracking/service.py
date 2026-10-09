from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain
from src.seo.keyword_tracking.constants import (
    BACKFILL_LOOKBACK,
    HISTORY_MONTHS,
    TRACKED_DEPTH,
    TRACKED_DEVICE,
    RankSource,
)
from src.seo.keyword_tracking.overview import months_back, stats, tracked_keywords
from src.seo.keyword_tracking.repositories.rankings import seo_rank_history
from src.seo.keyword_tracking.repositories.volumes import seo_volume_history
from src.seo.keyword_tracking.schemas import (
    Market,
    RankingsTracked,
    RankRow,
    TrackedOverview,
    TrackKeywordsRequest,
    VolumeRow,
    VolumesTracked,
)
from src.seo.keyword_tracking.shape import (
    clickstream_volume_rows,
    history_volume_rows,
    rank_rows,
)
from src.seo.market import country_of, markets
from src.sites.schemas import SiteRecord

VOLUME_FIELDS = ("search_volume", "clickstream_volume", "cpc", "competition")


def merged_volumes(rows: list[VolumeRow]) -> list[VolumeRow]:
    merged: dict[tuple, VolumeRow] = {}
    for row in rows:
        key = (row.keyword, row.location_code, row.language_code, row.month)
        found = merged.get(key)
        if found is None:
            merged[key] = row.model_copy()
            continue
        for field in VOLUME_FIELDS:
            if getattr(row, field) is not None:
                setattr(found, field, getattr(row, field))
    return list(merged.values())


class KeywordTrackingService:
    async def overview(
        self, db: AsyncSession, site: SiteRecord, location_code: int | None
    ) -> TrackedOverview:
        own = markets(site.markets, site.language)
        stored = {
            *(await seo_rank_history.markets(db, site.id)),
            *(await seo_volume_history.markets(db, site.id)),
        }
        known = list(
            dict.fromkeys([(m["location_code"], m["language_code"]) for m in own] + sorted(stored))
        )
        chosen = next((m for m in known if m[0] == location_code), known[0])
        today = datetime.now(UTC).date()
        months = months_back(today, HISTORY_MONTHS)
        days = await seo_rank_history.snapshot_days(db, site.id, *chosen, months[0])
        ranks = await seo_rank_history.site_rankings(db, site.id, *chosen, months[0])
        volumes = await seo_volume_history.months(db, site.id, *chosen, months[0])
        rows = tracked_keywords(months, days, ranks, volumes)
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

    async def track_rankings(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site_id: str,
        site_domain: str,
        body: TrackKeywordsRequest,
        targets: list[dict],
    ) -> RankingsTracked:
        site = own_domain(site_domain)
        today = datetime.now(UTC).date()
        rows: list[RankRow] = []
        backfilled: set[str] = set()
        snapshots = 0
        for market in targets:
            backfilled_before = await seo_rank_history.keywords_with_source(
                db,
                site_id,
                body.keywords,
                market["location_code"],
                market["language_code"],
                RankSource.HISTORY,
            )
            for keyword in body.keywords:
                if keyword not in backfilled_before:
                    since = (today - BACKFILL_LOOKBACK).isoformat()
                    for snapshot in await seo_data.historical_serps(
                        db, caller, keyword, market, since
                    ):
                        rows += rank_rows(
                            keyword, snapshot, market, RankSource.HISTORY, site, today
                        )
                        snapshots += 1
                    backfilled.add(keyword)
                live = await seo_data.serp_organic(
                    db, caller, keyword, TRACKED_DEVICE, TRACKED_DEPTH, market
                )
                if live is not None:
                    rows += rank_rows(keyword, live, market, RankSource.LIVE, site, today)
                    snapshots += 1
        saved = await seo_rank_history.upsert_many(db, user_id, site_id, rows)
        return RankingsTracked(
            keywords=len(body.keywords),
            backfilled=sorted(backfilled),
            snapshots=snapshots,
            rows=saved,
            site_ranked=sorted(
                {r.keyword for r in rows if r.is_site and r.source == RankSource.LIVE}
            ),
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
        for market in targets:
            for item in await seo_data.keyword_history(db, caller, body.keywords, market):
                rows += history_volume_rows(item, market)
            for item in await seo_data.keyword_overview(db, caller, body.keywords, market):
                rows += clickstream_volume_rows(item, market)
        merged = [r for r in merged_volumes(rows) if r.keyword]
        saved = await seo_volume_history.upsert_many(db, user_id, site_id, merged)
        found = {r.keyword for r in merged}
        return VolumesTracked(
            keywords=len(body.keywords),
            months=len({r.month for r in merged}),
            rows=saved,
            without_data=[k for k in body.keywords if k not in found],
        )


keyword_tracking_service = KeywordTrackingService()
