import math
import os
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_traffic import repository as repo
from src.site_traffic.reports import REPORT_SPECS, TRAFFIC_REPORTS
from src.site_traffic.schemas import (
    TrafficBreakdownResponse,
    TrafficChannelComparison,
    TrafficChannelTotals,
    TrafficContentPagesResponse,
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
from src.sites import repository as sites_repo
from src.sites.service import get_site

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


async def get_property(db: AsyncSession, user_id: str, site_id: str) -> TrafficPropertyResponse:
    site = await get_site(db, user_id, site_id)
    return TrafficPropertyResponse(property=site.ga_property, domain=site.domain)


async def set_property(
    db: AsyncSession, user_id: str, site_id: str, body: TrafficPropertyUpdateRequest
) -> TrafficPropertyUpdateResponse:
    await get_site(db, user_id, site_id)
    await sites_repo.merge_site(db, user_id, site_id, {"ga_property": body.property})
    return TrafficPropertyUpdateResponse(property=body.property)


async def _reap_syncs(db: AsyncSession) -> int:
    stale = await repo.stale_syncs(db, STALE_SYNC_MS)
    for sync in stale:
        await repo.patch_sync(
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


async def sync_jobs(db: AsyncSession, site_id: str) -> TrafficSyncJobsResponse:
    recent = await repo.list_syncs(db, site_id, limit=1)
    active = await repo.active_sync(db, site_id)
    return TrafficSyncJobsResponse(latest=recent[0] if recent else None, active=active)


async def get_sync(db: AsyncSession, site_id: str, id: str) -> TrafficSyncRecord:
    sync = await repo.get_sync(db, site_id, id)
    if sync is None:
        raise HTTPException(404, "No such traffic sync for this website.")
    return sync


async def start_sync(
    db: AsyncSession, user_id: str, site_id: str, trigger: str | None = None
) -> TrafficSyncStartResult:
    site = await get_site(db, user_id, site_id)
    await _reap_syncs(db)

    sync = await repo.insert_sync(db, user_id, site_id, trigger or "user")
    if sync is None:
        active = await repo.active_sync(db, site_id)
        return TrafficSyncStartResult(
            started=False,
            sync=active,
            reason=f"A traffic sync for {site.domain} is already running.",
        )
    return TrafficSyncStartResult(started=True, sync=sync)


async def claim_sync(
    db: AsyncSession, user_id: str, site_id: str, id: str
) -> TrafficSyncClaimResult:
    site = await get_site(db, user_id, site_id)
    sync = await get_sync(db, site_id, id)
    if sync.status != "queued":
        raise HTTPException(409, f"This sync is {sync.status}, not waiting to be claimed.")

    day_range = await repo.day_range(db, site_id)
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
    claimed = await repo.patch_sync(
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
    db: AsyncSession, user_id: str, site_id: str, id: str, body: TrafficSyncUpdateRequest
) -> TrafficSyncRecord:
    await get_sync(db, site_id, id)

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

    updated = await repo.patch_sync(db, site_id, id, patch)
    if updated is None:
        raise HTTPException(404, "No such traffic sync for this website.")
    return updated


async def ingest_rows(
    db: AsyncSession, user_id: str, site_id: str, body: TrafficRowsIngestRequest
) -> TrafficRowsIngestResponse:
    await get_site(db, user_id, site_id)
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

    for i in range(0, len(clean), repo.INSERT_CHUNK):
        await repo.upsert_report_chunk(
            db, user_id, site_id, body.report, clean[i : i + repo.INSERT_CHUNK]
        )
        await db.commit()
    return TrafficRowsIngestResponse(stored=len(clean))


async def export_rows(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    report: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TrafficRowsExportResponse:
    await get_site(db, user_id, site_id)
    if report not in TRAFFIC_REPORTS:
        raise HTTPException(400, f"report must be one of: {', '.join(TRAFFIC_REPORTS)}.")
    listed = await repo.list_report_rows(db, site_id, report, limit=limit, offset=offset)
    return TrafficRowsExportResponse(report=report, rows=listed.rows, total=listed.total)


async def overview(
    db: AsyncSession, user_id: str, site_id: str, days: int | None = None
) -> TrafficOverviewResponse:
    site = await get_site(db, user_id, site_id)
    span = _clamp_days(days)
    day_range = await repo.day_range(db, site_id)
    recent = await repo.list_syncs(db, site_id, limit=1)
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
    now = await repo.totals(db, site_id, last_day, span)
    before = await repo.totals(db, site_id, last_day, span, offset_days=span)
    organic_now = await repo.channel_totals(db, site_id, last_day, span, ORGANIC_CHANNEL)
    organic_before = await repo.channel_totals(
        db, site_id, last_day, span, ORGANIC_CHANNEL, offset_days=span
    )
    channels = await repo.rollup(db, site_id, "channel", last_day, span, limit=20)

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
    db: AsyncSession, user_id: str, site_id: str, days: int | None = None
) -> TrafficSeriesResponse:
    await get_site(db, user_id, site_id)
    span = _clamp_days(days)
    day_range = await repo.day_range(db, site_id)
    if not day_range.last_day:
        return TrafficSeriesResponse(days=span, last_day=None, points=[])
    points = await repo.daily_series(db, site_id, day_range.last_day, span, ORGANIC_CHANNEL)
    return TrafficSeriesResponse(days=span, last_day=day_range.last_day, points=points)


async def breakdown(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    by: str,
    days: int | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TrafficBreakdownResponse:
    await get_site(db, user_id, site_id)
    span = _clamp_days(days)
    day_range = await repo.day_range(db, site_id)
    if not day_range.last_day:
        return TrafficBreakdownResponse(by=by, days=span, last_day=None, rows=[], total=0)
    result = await repo.rollup(
        db,
        site_id,
        by,
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
    await get_site(db, user_id, site_id)
    span = _clamp_days(days)
    day_range = await repo.day_range(db, site_id)
    if not day_range.last_day:
        return TrafficLandingPagesResponse(pages=[], total=0, last_day=None, days=span)

    result = await repo.by_landing_page(
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
        pages=result.rows, total=result.total, last_day=day_range.last_day, days=span
    )


async def content_pages(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    days: int | None = None,
    search: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TrafficContentPagesResponse:
    await get_site(db, user_id, site_id)
    span = _clamp_days(days)
    day_range = await repo.day_range(db, site_id)
    if not day_range.last_day:
        return TrafficContentPagesResponse(pages=[], total=0, last_day=None, days=span)

    result = await repo.by_page_path(
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
