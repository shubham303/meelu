import math
import os
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_search import repository as repo
from src.site_search.schemas import (
    SearchChangesResponse,
    SearchInspectionsIngestRequest,
    SearchInspectionsIngestResponse,
    SearchInspectionTargetsResponse,
    SearchOverviewResponse,
    SearchPageDetailResponse,
    SearchPagesResponse,
    SearchPropertyRequest,
    SearchPropertyResponse,
    SearchQueriesResponse,
    SearchRowsIngestRequest,
    SearchRowsIngestResponse,
    SearchSeriesGroup,
    SearchSeriesPoint,
    SearchSeriesResponse,
    SearchSyncClaimResponse,
    SearchSyncJobsResponse,
    SearchSyncRecord,
    SearchSyncResponse,
    SearchSyncStartResponse,
    SearchSyncUpdateRequest,
)
from src.sites import repository as sites_repo
from src.sites.service import get_site

BACKFILL_MONTHS = 16
LAG_DAYS = 3
STALE_SYNC_MS = int(os.environ.get("MEELU_SEARCH_SYNC_STALE_MS") or 10 * 60 * 1000)
BLIND_IMPRESSIONS = 200
MAX_COMPARE_PAGES = 5
DEFAULT_INSPECTION_LIMIT = 300


def normalise_url(raw: str) -> str:
    try:
        parts = urlsplit(raw)
        if not parts.scheme or not parts.netloc:
            return raw.strip()
        path = parts.path or "/"
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))
    except ValueError:
        return raw.strip()


def _sync_response(sync: SearchSyncRecord | None) -> SearchSyncResponse | None:
    return None if sync is None else SearchSyncResponse.model_validate(sync)


def content_quality_verdict(indexation: dict[str, int]) -> str | None:
    crawled_not_indexed = indexation.get("crawled-not-indexed", 0)
    indexed = indexation.get("indexed", 0)
    if crawled_not_indexed >= 10 and crawled_not_indexed >= indexed * 0.1:
        return (
            f"{crawled_not_indexed} pages are crawled but not indexed — a content-quality "
            f"verdict, not a technical bug. It argues against publishing more of the same."
        )
    return None


def _iso(d: date) -> str:
    return d.isoformat()


def _end_day() -> str:
    return _iso((datetime.now(UTC) - timedelta(days=LAG_DAYS)).date())


def _backfill_start() -> str:
    today = datetime.now(UTC).date()
    months = today.year * 12 + (today.month - 1) - BACKFILL_MONTHS
    year, month0 = divmod(months, 12)
    return _iso(date(year, month0 + 1, 1) + timedelta(days=today.day - 1))


def _clamp_days(days: Any) -> int:
    try:
        n = float(days)
    except (TypeError, ValueError):
        return 90
    if not math.isfinite(n) or n <= 0:
        return 90
    return min(max(round(n), 7), 480)


def _not_found() -> HTTPException:
    return HTTPException(404, "No such search-data sync for this website.")


async def set_property(
    db: AsyncSession, user_id: str, site_id: str, body: SearchPropertyRequest
) -> SearchPropertyResponse:
    await get_site(db, user_id, site_id)
    await sites_repo.merge_site(db, user_id, site_id, {"gsc_property": body.property})
    return SearchPropertyResponse(property=body.property)


async def sync_jobs(db: AsyncSession, user_id: str, site_id: str) -> SearchSyncJobsResponse:
    await get_site(db, user_id, site_id)
    latest = await repo.latest_sync(db, site_id)
    active = await repo.active_sync(db, site_id)
    return SearchSyncJobsResponse(latest=_sync_response(latest), active=_sync_response(active))


async def get_sync(db: AsyncSession, user_id: str, site_id: str, id: str) -> SearchSyncRecord:
    await get_site(db, user_id, site_id)
    sync = await repo.get_sync(db, site_id, id)
    if sync is None:
        raise _not_found()
    return sync


async def start_sync(
    db: AsyncSession, user_id: str, site_id: str, trigger: str = "user"
) -> SearchSyncStartResponse:
    site = await get_site(db, user_id, site_id)
    await repo.reap_stalled_syncs(db, site_id, STALE_SYNC_MS)

    sync = await repo.open_sync(db, user_id, site_id, trigger)
    if sync is None:
        active = await repo.active_sync(db, site_id)
        return SearchSyncStartResponse(
            started=False,
            sync=_sync_response(active),
            reason=f"A search-data sync for {site.domain} is already running.",
        )
    return SearchSyncStartResponse(started=True, sync=_sync_response(sync))


async def claim_sync(
    db: AsyncSession, user_id: str, site_id: str, id: str
) -> SearchSyncClaimResponse:
    site = await get_site(db, user_id, site_id)
    sync = await repo.get_sync(db, site_id, id)
    if sync is None:
        raise _not_found()
    if sync.status != "queued":
        raise HTTPException(409, f"This sync is {sync.status}, not waiting to be claimed.")

    cov = await repo.coverage(db, site_id)
    start = _backfill_start()
    end = _end_day()
    resume_from = (
        _iso(date.fromisoformat(cov.last_day) + timedelta(days=1))
        if cov.last_day and cov.last_day >= start
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

    return SearchSyncClaimResponse(
        sync=SearchSyncResponse.model_validate(claimed or sync),
        property=site.gsc_property,
        domain=site.domain,
        start_day=frm,
        end_day=end,
        resume_from=resume_from,
        days_total=days_total,
    )


async def patch_sync(
    db: AsyncSession, user_id: str, site_id: str, id: str, body: SearchSyncUpdateRequest
) -> SearchSyncRecord:
    await get_site(db, user_id, site_id)
    sync = await repo.get_sync(db, site_id, id)
    if sync is None:
        raise _not_found()

    now = datetime.now(UTC)
    patch: dict[str, Any] = {"heartbeat_at": now}
    for key in ("days_done", "rows_stored", "pages_inspected", "property"):
        value = getattr(body, key)
        if value is not None:
            patch[key] = value
    if body.status:
        patch["status"] = body.status
        patch["finished_at"] = now
        if body.error is not None:
            patch["error"] = body.error
        if body.notes is not None:
            patch["notes"] = body.notes

    updated = await repo.patch_sync(db, site_id, id, patch)
    if updated is None:
        raise _not_found()
    return updated


async def ingest_days(
    db: AsyncSession, user_id: str, site_id: str, body: SearchRowsIngestRequest
) -> SearchRowsIngestResponse:
    await get_site(db, user_id, site_id)
    stored = 0
    for entry in body.days:
        stored += await repo.replace_day(db, user_id, site_id, entry.day, entry.rows)
        await db.commit()
    return SearchRowsIngestResponse(days=len(body.days), rows=stored)


async def ingest_inspections(
    db: AsyncSession, user_id: str, site_id: str, body: SearchInspectionsIngestRequest
) -> SearchInspectionsIngestResponse:
    await get_site(db, user_id, site_id)
    applied = await repo.apply_inspections(db, site_id, body.inspections)
    return SearchInspectionsIngestResponse(applied=applied)


async def inspection_targets(
    db: AsyncSession, user_id: str, site_id: str, limit: int | None
) -> SearchInspectionTargetsResponse:
    await get_site(db, user_id, site_id)
    span = limit if limit is not None and limit > 0 else DEFAULT_INSPECTION_LIMIT
    return SearchInspectionTargetsResponse(urls=await repo.inspection_targets(db, site_id, span))


async def overview(db: AsyncSession, user_id: str, site_id: str) -> SearchOverviewResponse:
    site = await get_site(db, user_id, site_id)
    cov = await repo.coverage(db, site_id)
    latest = await repo.latest_sync(db, site_id)
    sync = _sync_response(latest)
    active = sync if latest is not None and latest.status in ("queued", "running") else None

    if not cov.last_day:
        return SearchOverviewResponse(
            connected=bool(site.gsc_property),
            property=site.gsc_property,
            has_data=False,
            operating_blind=True,
            sync=sync,
            active=active,
        )

    current = await repo.totals_for_window(db, site_id, cov.last_day, 28)
    previous = await repo.totals_for_window(db, site_id, cov.last_day, 28, 28)
    weekly = await repo.weekly_clicks(db, site_id, cov.last_day, 12)
    indexation = await repo.indexation_counts(db, site_id)

    return SearchOverviewResponse(
        connected=bool(site.gsc_property),
        property=site.gsc_property,
        has_data=True,
        operating_blind=cov.impressions_28d < BLIND_IMPRESSIONS,
        first_day=cov.first_day,
        last_day=cov.last_day,
        days_stored=cov.days_stored,
        current=current,
        previous=previous,
        weekly_clicks=weekly,
        indexation=indexation.counts,
        never_checked=indexation.never_checked,
        google_prefers=indexation.google_prefers,
        content_quality_verdict=content_quality_verdict(indexation.counts),
        sync=sync,
        active=active,
    )


def _normalised_pages(pages: list[str] | None, verb: str) -> list[str]:
    normalised = [normalise_url(p) for p in (pages or [])]
    if len(normalised) > MAX_COMPARE_PAGES:
        raise HTTPException(400, f"At most {MAX_COMPARE_PAGES} pages can be {verb} at once.")
    return normalised


async def series(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    days: float | None = None,
    pages: list[str] | None = None,
) -> SearchSeriesResponse:
    await get_site(db, user_id, site_id)
    cov = await repo.coverage(db, site_id)
    if not cov.last_day:
        return SearchSeriesResponse(
            has_data=False, last_day=None, days=_clamp_days(days), series=[]
        )

    span = _clamp_days(days)
    normalised = _normalised_pages(pages, "compared")

    scope = normalised if normalised else None
    points = await repo.daily_series(db, site_id, cov.last_day, span, scope)
    current = await repo.totals_for_window(db, site_id, cov.last_day, span, 0, scope)
    previous = await repo.totals_for_window(db, site_id, cov.last_day, span, span, scope)

    cursor = date.fromisoformat(cov.last_day) - timedelta(days=span - 1)
    day_axis = [_iso(cursor + timedelta(days=i)) for i in range(span)]

    keys: list[str | None] = normalised if normalised else [None]
    grouped: list[SearchSeriesGroup] = []
    for key in keys:
        by_day = {p.day: p for p in points if key is None or p.page == key}
        day_points = []
        for day in day_axis:
            p = by_day.get(day)
            day_points.append(
                SearchSeriesPoint(
                    day=day,
                    clicks=p.clicks if p else 0,
                    impressions=p.impressions if p else 0,
                    ctr=(p.clicks / p.impressions) if p and p.impressions > 0 else None,
                    position=p.position if p else None,
                )
            )
        grouped.append(SearchSeriesGroup(page=key, points=day_points))

    return SearchSeriesResponse(
        has_data=True,
        last_day=cov.last_day,
        days=span,
        series=grouped,
        current=current,
        previous=previous,
    )


async def pages(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    days: float | None = None,
    sort: str | None = None,
    dir: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> SearchPagesResponse:
    await get_site(db, user_id, site_id)
    cov = await repo.coverage(db, site_id)
    if not cov.last_day:
        return SearchPagesResponse(rows=[], total=0, last_day=None)
    span = _clamp_days(days)
    rollup = await repo.pages_rollup(
        db,
        site_id,
        cov.last_day,
        span,
        limit=limit,
        offset=offset,
        sort=sort,
        dir=dir,
        search=search,
    )
    return SearchPagesResponse(
        rows=rollup.rows, total=rollup.total, last_day=cov.last_day, days=span
    )


async def page_detail(
    db: AsyncSession, user_id: str, site_id: str, url: str, days: float | None = None
) -> SearchPageDetailResponse:
    await get_site(db, user_id, site_id)
    cov = await repo.coverage(db, site_id)
    page = normalise_url(url)
    if not cov.last_day:
        return SearchPageDetailResponse(page=page, queries=[], last_day=None, has_data=False)
    span = _clamp_days(days)
    rollup = await repo.queries_rollup(db, site_id, cov.last_day, span, page=page, limit=100)
    return SearchPageDetailResponse(
        page=page, queries=rollup.rows, last_day=cov.last_day, days=span, has_data=True
    )


async def queries(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    view: str | None = None,
    days: float | None = None,
    pages_in: list[str] | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> SearchQueriesResponse:
    await get_site(db, user_id, site_id)
    cov = await repo.coverage(db, site_id)
    if not cov.last_day:
        return SearchQueriesResponse(rows=[], total=0, last_day=None)
    span = _clamp_days(days if days is not None else (28 if view == "striking" else 90))
    normalised = _normalised_pages(pages_in, "filtered")
    rollup = await repo.queries_rollup(
        db,
        site_id,
        cov.last_day,
        span,
        view=view,
        pages=normalised if normalised else None,
        search=search,
        limit=limit,
        offset=offset,
    )
    return SearchQueriesResponse(
        rows=rollup.rows, total=rollup.total, last_day=cov.last_day, days=span
    )


async def changes(
    db: AsyncSession, user_id: str, site_id: str, days: float | None = None
) -> SearchChangesResponse:
    await get_site(db, user_id, site_id)
    cov = await repo.coverage(db, site_id)
    if not cov.last_day:
        return SearchChangesResponse(up=[], down=[], last_day=None, has_data=False)
    span = _clamp_days(days if days is not None else 90)
    result = await repo.movers(db, site_id, cov.last_day, span)
    return SearchChangesResponse(
        up=result.up, down=result.down, last_day=cov.last_day, days=span, has_data=True
    )
