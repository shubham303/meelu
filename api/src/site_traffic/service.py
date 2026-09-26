import math
import os
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageBrief
from src.site_traffic.reports import REPORT_SPECS, TRAFFIC_REPORTS
from src.site_traffic.repositories.base import TrafficDailyRepository, TrafficRollupRepository
from src.site_traffic.repositories.site_traffic_channels_daily import site_traffic_channels_dailies
from src.site_traffic.repositories.site_traffic_events_daily import site_traffic_events_dailies
from src.site_traffic.repositories.site_traffic_geo_daily import site_traffic_geo_dailies
from src.site_traffic.repositories.site_traffic_landing_daily import site_traffic_landing_dailies
from src.site_traffic.repositories.site_traffic_pages_daily import site_traffic_pages_dailies
from src.site_traffic.repositories.site_traffic_sync import site_traffic_syncs
from src.site_traffic.repositories.site_traffic_tech_daily import site_traffic_tech_dailies
from src.site_traffic.repositories.site_traffic_totals_daily import site_traffic_totals_dailies
from src.site_traffic.schemas import (
    TrafficBreakdownResponse,
    TrafficChannelComparison,
    TrafficChannelTotals,
    TrafficContentPagesResponse,
    TrafficLandingPageRow,
    TrafficLandingPagesResponse,
    TrafficOverviewResponse,
    TrafficPropertyResponse,
    TrafficPropertyUpdateRequest,
    TrafficPropertyUpdateResponse,
    TrafficRowsExportResponse,
    TrafficRowsIngestRequest,
    TrafficRowsIngestResponse,
    TrafficSeriesResponse,
    TrafficSyncClaimResult,
    TrafficSyncJobsResponse,
    TrafficSyncRecord,
    TrafficSyncStartResult,
    TrafficSyncUpdateRequest,
    TrafficTotals,
    TrafficTotalsComparison,
)
from src.sites.repository import sites
from src.sites.service import site_service

BACKFILL_MONTHS = 16
LAG_DAYS = 2
STALE_SYNC_MS = int(os.environ.get("MEELU_TRAFFIC_SYNC_STALE_MS") or 10 * 60 * 1000)
ORGANIC_CHANNEL = "Organic Search"
DEFAULT_WINDOW_DAYS = 28

TEXT_CAPS = {
    "landingPage": 2048,
    "pagePath": 2048,
    "channel": 256,
    "source": 512,
    "medium": 256,
    "eventName": 256,
    "country": 256,
    "deviceCategory": 128,
    "os": 128,
    "browser": 128,
}

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HOST_RE = re.compile(r"^https?://[^/]+")

REPORT_REPOSITORIES: dict[str, TrafficDailyRepository] = {
    "totals": site_traffic_totals_dailies,
    "channels": site_traffic_channels_dailies,
    "landing": site_traffic_landing_dailies,
    "pages": site_traffic_pages_dailies,
    "events": site_traffic_events_dailies,
    "geo": site_traffic_geo_dailies,
    "tech": site_traffic_tech_dailies,
}

BREAKDOWNS: dict[str, tuple[TrafficRollupRepository, tuple[str, ...]]] = {
    "channel": (site_traffic_channels_dailies, ("channel",)),
    "source": (site_traffic_channels_dailies, ("source", "medium")),
    "event": (site_traffic_events_dailies, ("event_name",)),
    "country": (site_traffic_geo_dailies, ("country",)),
    "device": (site_traffic_tech_dailies, ("device_category",)),
    "os": (site_traffic_tech_dailies, ("os",)),
    "browser": (site_traffic_tech_dailies, ("browser",)),
}


def _iso(d: date) -> str:
    return d.isoformat()


def _end_day() -> str:
    return _iso((datetime.now(UTC) - timedelta(days=LAG_DAYS)).date())


def _backfill_start() -> str:
    today = datetime.now(UTC).date()
    months = today.year * 12 + (today.month - 1) - BACKFILL_MONTHS
    year, month0 = divmod(months, 12)
    return _iso(date(year, month0 + 1, 1) + timedelta(days=today.day - 1))


def _clamp_days(days: int | None) -> int:
    if days is None or days <= 0:
        return DEFAULT_WINDOW_DAYS
    return min(max(days, 7), 480)


def _landing_key(landing_page: str) -> str:
    return landing_page.split("?", 1)[0].rstrip("/")


def _url_path_key(url: str) -> str:
    return HOST_RE.sub("", url).rstrip("/")


def _num(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else 0.0
    if isinstance(value, str):
        try:
            n = float(value)
        except ValueError:
            return 0.0
        return n if math.isfinite(n) else 0.0
    return 0.0


class SiteTrafficService:
    async def get_property(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> TrafficPropertyResponse:
        site = await site_service.get(db, user_id, site_id)
        return TrafficPropertyResponse(property=site.ga_property, domain=site.domain)

    async def set_property(
        self, db: AsyncSession, user_id: str, site_id: str, body: TrafficPropertyUpdateRequest
    ) -> TrafficPropertyUpdateResponse:
        await site_service.get(db, user_id, site_id)
        await sites.merge(db, user_id, site_id, {"ga_property": body.property})
        return TrafficPropertyUpdateResponse(property=body.property)

    async def _reap_syncs(self, db: AsyncSession) -> int:
        stale = await site_traffic_syncs.list_stale(db, STALE_SYNC_MS)
        for sync in stale:
            await site_traffic_syncs.update(
                db,
                sync.site_id,
                sync.id,
                {
                    "status": "failed",
                    "error": "the process running it stopped reporting",
                    "finished_at": datetime.now(UTC),
                },
            )
        return len(stale)

    async def sync_jobs(self, db: AsyncSession, site_id: str) -> TrafficSyncJobsResponse:
        recent = await site_traffic_syncs.list_recent(db, site_id, limit=1)
        active = await site_traffic_syncs.active(db, site_id)
        return TrafficSyncJobsResponse(latest=recent[0] if recent else None, active=active)

    async def get_sync(self, db: AsyncSession, site_id: str, id: str) -> TrafficSyncRecord:
        sync = await site_traffic_syncs.get(db, site_id, id)
        if sync is None:
            raise HTTPException(404, "No such traffic sync for this website.")
        return sync

    async def start_sync(
        self, db: AsyncSession, user_id: str, site_id: str, trigger: str | None = None
    ) -> TrafficSyncStartResult:
        site = await site_service.get(db, user_id, site_id)
        await self._reap_syncs(db)

        sync = await site_traffic_syncs.create(db, user_id, site_id, trigger or "user")
        if sync is None:
            active = await site_traffic_syncs.active(db, site_id)
            return TrafficSyncStartResult(
                started=False,
                sync=active,
                reason=f"A traffic sync for {site.domain} is already running.",
            )
        return TrafficSyncStartResult(started=True, sync=sync)

    async def claim_sync(
        self, db: AsyncSession, user_id: str, site_id: str, id: str
    ) -> TrafficSyncClaimResult:
        site = await site_service.get(db, user_id, site_id)
        sync = await self.get_sync(db, site_id, id)
        if sync.status != "queued":
            raise HTTPException(409, f"This sync is {sync.status}, not waiting to be claimed.")

        day_range = await site_traffic_totals_dailies.day_range(db, site_id)
        start = _backfill_start()
        end = _end_day()
        resume_from = (
            _iso(date.fromisoformat(day_range.last_day) + timedelta(days=1))
            if day_range.last_day and day_range.last_day >= start
            else None
        )
        frm = resume_from or start
        days_total = max(0, (date.fromisoformat(end) - date.fromisoformat(frm)).days + 1)

        now = datetime.now(UTC)
        claimed = await site_traffic_syncs.update(
            db,
            site_id,
            id,
            {
                "status": "running",
                "started_at": now,
                "heartbeat_at": now,
                "days_total": days_total,
                "first_day": frm,
                "last_day": end,
            },
        )

        return TrafficSyncClaimResult(
            sync=claimed or sync,
            property=site.ga_property,
            domain=site.domain,
            start_day=frm,
            end_day=end,
            resume_from=resume_from,
            days_total=days_total,
        )

    async def patch_sync(
        self, db: AsyncSession, user_id: str, site_id: str, id: str, body: TrafficSyncUpdateRequest
    ) -> TrafficSyncRecord:
        await self.get_sync(db, site_id, id)

        patch: dict[str, Any] = {"heartbeat_at": datetime.now(UTC)}
        if body.days_done is not None:
            patch["days_done"] = body.days_done
        if body.rows_stored is not None:
            patch["rows_stored"] = body.rows_stored
        if body.property is not None:
            patch["property"] = body.property

        if body.status:
            patch["status"] = body.status
            patch["finished_at"] = datetime.now(UTC)
            if body.error is not None:
                patch["error"] = body.error
            if body.notes is not None:
                patch["notes"] = body.notes

        updated = await site_traffic_syncs.update(db, site_id, id, patch)
        if updated is None:
            raise HTTPException(404, "No such traffic sync for this website.")
        return updated

    async def ingest_rows(
        self, db: AsyncSession, user_id: str, site_id: str, body: TrafficRowsIngestRequest
    ) -> TrafficRowsIngestResponse:
        await site_service.get(db, user_id, site_id)
        spec = REPORT_SPECS[body.report]

        clean: list[dict[str, Any]] = []
        for r in body.rows:
            day = str(r.get("day") or "")
            if not DAY_RE.match(day):
                raise HTTPException(400, f'"{day}" is not a YYYY-MM-DD day.')
            out: dict[str, Any] = {"day": day}
            skip = False
            for dim in spec.dims:
                raw = r.get(dim)
                value = ("" if raw is None else str(raw))[: TEXT_CAPS.get(dim, 256)]
                if not value:
                    skip = True
                out[dim] = value
            if skip:
                continue
            for metric in spec.metrics:
                out[metric] = max(0.0, _num(r.get(metric)))
            clean.append(out)

        repository = REPORT_REPOSITORIES[body.report]
        for i in range(0, len(clean), repository.INSERT_CHUNK):
            await repository.upsert_chunk(
                db, user_id, site_id, clean[i : i + repository.INSERT_CHUNK]
            )
            await db.commit()
        return TrafficRowsIngestResponse(stored=len(clean))

    async def export_rows(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        report: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficRowsExportResponse:
        await site_service.get(db, user_id, site_id)
        if report not in TRAFFIC_REPORTS:
            raise HTTPException(400, f"report must be one of: {', '.join(TRAFFIC_REPORTS)}.")
        listed = await REPORT_REPOSITORIES[report].list_rows(
            db, site_id, limit=limit, offset=offset
        )
        return TrafficRowsExportResponse(report=report, rows=listed.rows, total=listed.total)

    async def overview(
        self, db: AsyncSession, user_id: str, site_id: str, days: int | None = None
    ) -> TrafficOverviewResponse:
        site = await site_service.get(db, user_id, site_id)
        span = _clamp_days(days)
        day_range = await site_traffic_totals_dailies.day_range(db, site_id)
        recent = await site_traffic_syncs.list_recent(db, site_id, limit=1)
        sync = recent[0] if recent else None
        active = sync if sync is not None and sync.status in ("queued", "running") else None

        if not day_range.last_day:
            return TrafficOverviewResponse(
                connected=bool(site.ga_property),
                property=site.ga_property,
                has_data=False,
                days=span,
                first_day=None,
                last_day=None,
                days_stored=0,
                totals=TrafficTotalsComparison(current=TrafficTotals(), previous=TrafficTotals()),
                organic=TrafficChannelComparison(
                    current=TrafficChannelTotals(), previous=TrafficChannelTotals()
                ),
                channels=[],
                sync=sync,
                active=active,
            )

        last_day = day_range.last_day
        now = await site_traffic_totals_dailies.totals(db, site_id, last_day, span)
        before = await site_traffic_totals_dailies.totals(
            db, site_id, last_day, span, offset_days=span
        )
        organic_now = await site_traffic_channels_dailies.channel_totals(
            db, site_id, last_day, span, ORGANIC_CHANNEL
        )
        organic_before = await site_traffic_channels_dailies.channel_totals(
            db, site_id, last_day, span, ORGANIC_CHANNEL, offset_days=span
        )
        channels = await site_traffic_channels_dailies.rollup(
            db, site_id, ("channel",), last_day, span, limit=20
        )

        return TrafficOverviewResponse(
            connected=bool(site.ga_property),
            property=site.ga_property,
            has_data=True,
            days=span,
            first_day=day_range.first_day,
            last_day=last_day,
            days_stored=day_range.days_stored,
            totals=TrafficTotalsComparison(current=now, previous=before),
            organic=TrafficChannelComparison(current=organic_now, previous=organic_before),
            channels=channels.rows,
            sync=sync,
            active=active,
        )

    async def series(
        self, db: AsyncSession, user_id: str, site_id: str, days: int | None = None
    ) -> TrafficSeriesResponse:
        await site_service.get(db, user_id, site_id)
        span = _clamp_days(days)
        day_range = await site_traffic_totals_dailies.day_range(db, site_id)
        if not day_range.last_day:
            return TrafficSeriesResponse(days=span, last_day=None, points=[])
        totals = await site_traffic_totals_dailies.series(db, site_id, day_range.last_day, span)
        organic = await site_traffic_channels_dailies.daily_sessions_for_channel(
            db, site_id, ORGANIC_CHANNEL, day_range.last_day, span
        )
        points = [p.model_copy(update={"organic_sessions": organic.get(p.day, 0)}) for p in totals]
        return TrafficSeriesResponse(days=span, last_day=day_range.last_day, points=points)

    async def breakdown(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        by: str,
        days: int | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficBreakdownResponse:
        await site_service.get(db, user_id, site_id)
        span = _clamp_days(days)
        day_range = await site_traffic_totals_dailies.day_range(db, site_id)
        if not day_range.last_day:
            return TrafficBreakdownResponse(by=by, days=span, last_day=None, rows=[], total=0)
        repository, dims = BREAKDOWNS[by]
        result = await repository.rollup(
            db,
            site_id,
            dims,
            day_range.last_day,
            span,
            limit=limit,
            offset=offset,
            search=search,
        )
        return TrafficBreakdownResponse(
            by=by, days=span, last_day=day_range.last_day, rows=result.rows, total=result.total
        )

    async def landing_pages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        days: int | None = None,
        channel: str | None = None,
        search: str | None = None,
        sort: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficLandingPagesResponse:
        await site_service.get(db, user_id, site_id)
        span = _clamp_days(days)
        day_range = await site_traffic_totals_dailies.day_range(db, site_id)
        if not day_range.last_day:
            return TrafficLandingPagesResponse(pages=[], total=0, last_day=None, days=span)

        result = await site_traffic_landing_dailies.by_landing_page(
            db,
            site_id,
            day_range.last_day,
            span,
            channel=channel,
            search=search,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return TrafficLandingPagesResponse(
            pages=await self._with_pages(db, site_id, result.rows),
            total=result.total,
            last_day=day_range.last_day,
            days=span,
        )

    async def _with_pages(
        self, db: AsyncSession, site_id: str, rows: list[TrafficLandingPageRow]
    ) -> list[TrafficLandingPageRow]:
        if not rows:
            return []
        found = await site_pages.list_by_paths(
            db, site_id, list(dict.fromkeys(_landing_key(r.landing_page) for r in rows))
        )
        by_path: dict[str, SitePageBrief] = {}
        for page in found:
            by_path.setdefault(_url_path_key(page.url), page)
        enriched = []
        for row in rows:
            page = by_path.get(_landing_key(row.landing_page))
            enriched.append(
                row.model_copy(
                    update={
                        "page_id": page.id if page else None,
                        "url": page.url if page else None,
                        "title": page.title if page else None,
                    }
                )
            )
        return enriched

    async def content_pages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        days: int | None = None,
        search: str | None = None,
        sort: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficContentPagesResponse:
        await site_service.get(db, user_id, site_id)
        span = _clamp_days(days)
        day_range = await site_traffic_totals_dailies.day_range(db, site_id)
        if not day_range.last_day:
            return TrafficContentPagesResponse(pages=[], total=0, last_day=None, days=span)

        result = await site_traffic_pages_dailies.by_page_path(
            db,
            site_id,
            day_range.last_day,
            span,
            search=search,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        return TrafficContentPagesResponse(
            pages=result.rows, total=result.total, last_day=day_range.last_day, days=span
        )


site_traffic_service = SiteTrafficService()
