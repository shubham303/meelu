import math
import os
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.precompute.service import seo_precompute_service
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageBrief
from src.site_search.repositories.site_page_index_status import site_page_index_statuses
from src.site_search.repositories.site_search_daily import site_search_dailies, strip_slash
from src.site_search.repositories.site_search_sync import site_search_syncs
from src.site_search.schemas import (
    GooglePreferredCanonical,
    IndexationSummary,
    NewSitePageIndexStatus,
    SearchChangesResponse,
    SearchInspectionsIngestRequest,
    SearchInspectionsIngestResponse,
    SearchInspectionTargetsResponse,
    SearchOverviewResponse,
    SearchPageDetailResponse,
    SearchPageRollupRow,
    SearchPagesResponse,
    SearchPropertyRequest,
    SearchPropertyResponse,
    SearchQueriesResponse,
    SearchQueryRollup,
    SearchQueryRollupRow,
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
    SitePageIndexStatusRecord,
)
from src.sites.repository import sites
from src.sites.service import site_service

BACKFILL_MONTHS = 16
LAG_DAYS = 3
STALE_SYNC_MS = int(os.environ.get("MEELU_SEARCH_SYNC_STALE_MS") or 10 * 60 * 1000)
BLIND_IMPRESSIONS = 200
MAX_COMPARE_PAGES = 5
DEFAULT_INSPECTION_LIMIT = 300
MAX_INSPECTION_LIMIT = 1000
REINSPECT_AFTER_DAYS = 14
GOOGLE_PREFERS_LIMIT = 10
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
PAGE_DETAIL_QUERIES = 100
STATUS_SORTS = {
    "index": "index_state",
    "crawled": "last_crawl_time",
    "inspected": "index_checked_at",
}
STALLED_SYNC_ERROR = "the process running it stopped reporting"
EXCLUDED_HINTS = (
    "noindex",
    "duplicate",
    "alternate",
    "canonical",
    "redirect",
    "excluded",
    "not found",
    "soft 404",
)


def classify_coverage(verdict: str | None, coverage_state: str | None) -> str:
    state = (coverage_state or "").lower()
    if verdict == "PASS":
        return "indexed"
    if "crawled" in state and "not indexed" in state:
        return "crawled-not-indexed"
    if "discovered" in state:
        return "discovered"
    if "unknown to google" in state:
        return "unknown-to-google"
    if "blocked" in state or "robots" in state:
        return "blocked"
    if any(hint in state for hint in EXCLUDED_HINTS):
        return "excluded"
    return "unknown"


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


def _page_bounds(limit: int | None, offset: int | None) -> tuple[int, int]:
    return (
        min(max(limit if limit is not None else DEFAULT_PAGE_SIZE, 1), MAX_PAGE_SIZE),
        max(offset if offset is not None else 0, 0),
    )


def _pg_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    at = value.astimezone(UTC) if value.tzinfo is not None else value
    stamp = at.strftime("%Y-%m-%d %H:%M:%S")
    if at.microsecond:
        stamp += f".{at.microsecond:06d}".rstrip("0")
    return f"{stamp}+00"


def _not_found() -> HTTPException:
    return HTTPException(404, "No such search-data sync for this website.")


class SiteSearchService:
    async def set_property(
        self, db: AsyncSession, user_id: str, site_id: str, body: SearchPropertyRequest
    ) -> SearchPropertyResponse:
        await site_service.get(db, user_id, site_id)
        await sites.merge(db, user_id, site_id, {"gsc_property": body.property})
        return SearchPropertyResponse(property=body.property)

    async def sync_jobs(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> SearchSyncJobsResponse:
        await site_service.get(db, user_id, site_id)
        latest = await site_search_syncs.latest(db, site_id)
        active = await site_search_syncs.active(db, site_id)
        return SearchSyncJobsResponse(latest=_sync_response(latest), active=_sync_response(active))

    async def get_sync(
        self, db: AsyncSession, user_id: str, site_id: str, id: str
    ) -> SearchSyncRecord:
        await site_service.get(db, user_id, site_id)
        sync = await site_search_syncs.get(db, site_id, id)
        if sync is None:
            raise _not_found()
        return sync

    async def start_sync(
        self, db: AsyncSession, user_id: str, site_id: str, trigger: str = "user"
    ) -> SearchSyncStartResponse:
        site = await site_service.get(db, user_id, site_id)
        await site_search_syncs.fail_stalled(db, site_id, STALE_SYNC_MS, STALLED_SYNC_ERROR)

        sync = await site_search_syncs.create(db, user_id, site_id, trigger)
        if sync is None:
            active = await site_search_syncs.active(db, site_id)
            return SearchSyncStartResponse(
                started=False,
                sync=_sync_response(active),
                reason=f"A search-data sync for {site.domain} is already running.",
            )
        return SearchSyncStartResponse(started=True, sync=_sync_response(sync))

    async def claim_sync(
        self, db: AsyncSession, user_id: str, site_id: str, id: str
    ) -> SearchSyncClaimResponse:
        site = await site_service.get(db, user_id, site_id)
        sync = await site_search_syncs.get(db, site_id, id)
        if sync is None:
            raise _not_found()
        if sync.status != "queued":
            raise HTTPException(409, f"This sync is {sync.status}, not waiting to be claimed.")

        cov = await site_search_dailies.coverage(db, site_id)
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
        claimed = await site_search_syncs.update(
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
        self, db: AsyncSession, user_id: str, site_id: str, id: str, body: SearchSyncUpdateRequest
    ) -> SearchSyncRecord:
        await site_service.get(db, user_id, site_id)
        sync = await site_search_syncs.get(db, site_id, id)
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

        updated = await site_search_syncs.update(db, site_id, id, patch)
        if updated is None:
            raise _not_found()
        if body.status == "completed":
            await seo_precompute_service.run_rollup(db, user_id, site_id)
        return updated

    async def ingest_days(
        self, db: AsyncSession, user_id: str, site_id: str, body: SearchRowsIngestRequest
    ) -> SearchRowsIngestResponse:
        await site_service.get(db, user_id, site_id)
        stored = 0
        for entry in body.days:
            stored += await site_search_dailies.replace_day(
                db, user_id, site_id, entry.day, entry.rows
            )
            await db.commit()
        return SearchRowsIngestResponse(days=len(body.days), rows=stored)

    async def ingest_inspections(
        self, db: AsyncSession, user_id: str, site_id: str, body: SearchInspectionsIngestRequest
    ) -> SearchInspectionsIngestResponse:
        await site_service.get(db, user_id, site_id)
        rows = [
            NewSitePageIndexStatus(
                url=r.url,
                index_state=classify_coverage(r.verdict, r.coverage_state),
                coverage_state=r.coverage_state,
                google_canonical=r.google_canonical,
                last_crawl_time=r.last_crawl_time,
            )
            for r in body.inspections
        ]
        by_url = {strip_slash(r.url): r for r in rows}
        found = await site_pages.list_by_urls(db, site_id, list(by_url), strip_trailing_slash=True)
        by_page = {p.id: by_url[strip_slash(p.url)] for p in found if strip_slash(p.url) in by_url}
        applied = await site_page_index_statuses.upsert_many(db, user_id, site_id, by_page)
        return SearchInspectionsIngestResponse(applied=applied)

    async def inspection_targets(
        self, db: AsyncSession, user_id: str, site_id: str, limit: int | None
    ) -> SearchInspectionTargetsResponse:
        await site_service.get(db, user_id, site_id)
        span = limit if limit is not None and limit > 0 else DEFAULT_INSPECTION_LIMIT
        span = min(max(span, 1), MAX_INSPECTION_LIMIT)
        live = [p for p in await site_pages.list_live(db, site_id) if p.fetch_error is None]
        checked = {
            s.page_id: s.index_checked_at
            for s in await site_page_index_statuses.list_for_site(db, site_id)
        }
        cutoff = datetime.now(UTC) - timedelta(days=REINSPECT_AFTER_DAYS)
        due = [
            (p, checked.get(p.id))
            for p in live
            if checked.get(p.id) is None or checked[p.id] < cutoff
        ]
        due.sort(key=lambda d: (d[1] is not None, d[1] or cutoff, -d[0].inlinks))
        return SearchInspectionTargetsResponse(urls=[p.url for p, _ in due[:span]])

    async def _indexation(self, db: AsyncSession, site_id: str) -> IndexationSummary:
        live = await site_pages.list_live(db, site_id)
        statuses = {s.page_id: s for s in await site_page_index_statuses.list_for_site(db, site_id)}
        counts: dict[str, int] = {}
        prefers: list[tuple[SitePageBrief, SitePageIndexStatusRecord]] = []
        for page in live:
            status = statuses.get(page.id)
            state = (
                status.index_state
                if status is not None and status.index_state is not None
                else "unchecked"
            )
            counts[state] = counts.get(state, 0) + 1
            if (
                status is not None
                and status.google_canonical
                and status.google_canonical != page.url
            ):
                prefers.append((page, status))
        prefers.sort(key=lambda item: item[0].inlinks, reverse=True)
        return IndexationSummary(
            counts=counts,
            never_checked=counts.get("unchecked", 0),
            google_prefers=[
                GooglePreferredCanonical(
                    url=page.url,
                    google_canonical=status.google_canonical,
                    coverage_state=status.coverage_state,
                )
                for page, status in prefers[:GOOGLE_PREFERS_LIMIT]
            ],
        )

    async def overview(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> SearchOverviewResponse:
        site = await site_service.get(db, user_id, site_id)
        cov = await site_search_dailies.coverage(db, site_id)
        latest = await site_search_syncs.latest(db, site_id)
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

        current = await site_search_dailies.totals_for_window(db, site_id, cov.last_day, 28)
        previous = await site_search_dailies.totals_for_window(db, site_id, cov.last_day, 28, 28)
        weekly = await site_search_dailies.weekly_clicks(db, site_id, cov.last_day, 12)
        indexation = await self._indexation(db, site_id)

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

    def _normalised_pages(self, pages: list[str] | None, verb: str) -> list[str]:
        normalised = [normalise_url(p) for p in (pages or [])]
        if len(normalised) > MAX_COMPARE_PAGES:
            raise HTTPException(400, f"At most {MAX_COMPARE_PAGES} pages can be {verb} at once.")
        return normalised

    async def series(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        days: float | None = None,
        pages: list[str] | None = None,
    ) -> SearchSeriesResponse:
        await site_service.get(db, user_id, site_id)
        cov = await site_search_dailies.coverage(db, site_id)
        if not cov.last_day:
            return SearchSeriesResponse(
                has_data=False, last_day=None, days=_clamp_days(days), series=[]
            )

        span = _clamp_days(days)
        normalised = self._normalised_pages(pages, "compared")

        scope = normalised if normalised else None
        points = await site_search_dailies.daily_series(db, site_id, cov.last_day, span, scope)
        current = await site_search_dailies.totals_for_window(
            db, site_id, cov.last_day, span, 0, scope
        )
        previous = await site_search_dailies.totals_for_window(
            db, site_id, cov.last_day, span, span, scope
        )

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
        self,
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
        await site_service.get(db, user_id, site_id)
        cov = await site_search_dailies.coverage(db, site_id)
        if not cov.last_day:
            return SearchPagesResponse(rows=[], total=0, last_day=None)
        span = _clamp_days(days)
        limit, offset = _page_bounds(limit, offset)
        direction = dir if dir is not None else ("asc" if sort == "page" else "desc")
        direction = "asc" if direction == "asc" else "desc"
        status_field = STATUS_SORTS.get(sort or "")
        if status_field is None:
            rollup = await site_search_dailies.pages_rollup(
                db,
                site_id,
                cov.last_day,
                span,
                search=search,
                limit=limit,
                offset=offset,
                sort=sort,
                dir=direction,
            )
            enriched = await self._enrich_pages(db, site_id, rollup.rows)
            return SearchPagesResponse(
                rows=[row for row, _ in enriched],
                total=rollup.total,
                last_day=cov.last_day,
                days=span,
            )

        rollup = await site_search_dailies.pages_rollup(
            db, site_id, cov.last_day, span, search=search
        )
        enriched = await self._enrich_pages(db, site_id, rollup.rows)
        known = [
            (row, getattr(status, status_field))
            for row, status in enriched
            if status is not None and getattr(status, status_field) is not None
        ]
        unknown = [
            row
            for row, status in enriched
            if status is None or getattr(status, status_field) is None
        ]
        known.sort(key=lambda item: item[1], reverse=direction == "desc")
        ordered = [row for row, _ in known] + unknown
        window = ordered[offset : offset + limit]
        return SearchPagesResponse(
            rows=window,
            total=rollup.total if window else 0,
            last_day=cov.last_day,
            days=span,
        )

    async def _pages_by_url(
        self, db: AsyncSession, site_id: str, urls: list[str]
    ) -> dict[str, SitePageBrief]:
        found = await site_pages.list_by_urls(
            db, site_id, list(dict.fromkeys(urls)), strip_trailing_slash=True
        )
        by_url: dict[str, SitePageBrief] = {}
        for page in found:
            by_url.setdefault(strip_slash(page.url), page)
        return by_url

    async def _enrich_pages(
        self, db: AsyncSession, site_id: str, rows: list[SearchPageRollupRow]
    ) -> list[tuple[SearchPageRollupRow, SitePageIndexStatusRecord | None]]:
        if not rows:
            return []
        by_url = await self._pages_by_url(db, site_id, [r.page for r in rows])
        statuses = {
            s.page_id: s
            for s in await site_page_index_statuses.list_by_page_ids(
                db, site_id, [p.id for p in by_url.values()]
            )
        }
        enriched: list[tuple[SearchPageRollupRow, SitePageIndexStatusRecord | None]] = []
        for row in rows:
            page = by_url.get(strip_slash(row.page))
            status = statuses.get(page.id) if page is not None else None
            enriched.append(
                (
                    row.model_copy(
                        update={
                            "page_id": page.id if page else None,
                            "title": page.title if page else None,
                            "inlinks": page.inlinks if page else None,
                            "index_state": status.index_state if status else None,
                            "coverage_state": status.coverage_state if status else None,
                            "google_canonical": status.google_canonical if status else None,
                            "last_crawl_time": _pg_text(status.last_crawl_time) if status else None,
                            "index_checked_at": _pg_text(status.index_checked_at)
                            if status
                            else None,
                        }
                    ),
                    status,
                )
            )
        return enriched

    async def _enrich_queries(
        self, db: AsyncSession, site_id: str, rollup: SearchQueryRollup
    ) -> list[SearchQueryRollupRow]:
        by_url = await self._pages_by_url(db, site_id, [r.page for r in rollup.rows if r.page])
        rows = []
        for row in rollup.rows:
            page = by_url.get(strip_slash(row.page)) if row.page else None
            rows.append(
                row.model_copy(
                    update={
                        "page_id": page.id if page else None,
                        "inlinks": page.inlinks if page else None,
                    }
                )
            )
        return rows

    async def page_detail(
        self, db: AsyncSession, user_id: str, site_id: str, url: str, days: float | None = None
    ) -> SearchPageDetailResponse:
        await site_service.get(db, user_id, site_id)
        cov = await site_search_dailies.coverage(db, site_id)
        page = normalise_url(url)
        if not cov.last_day:
            return SearchPageDetailResponse(page=page, queries=[], last_day=None, has_data=False)
        span = _clamp_days(days)
        rollup = await site_search_dailies.queries_rollup(
            db, site_id, cov.last_day, span, page=page, limit=PAGE_DETAIL_QUERIES
        )
        return SearchPageDetailResponse(
            page=page,
            queries=await self._enrich_queries(db, site_id, rollup),
            last_day=cov.last_day,
            days=span,
            has_data=True,
        )

    async def queries(
        self,
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
        await site_service.get(db, user_id, site_id)
        cov = await site_search_dailies.coverage(db, site_id)
        if not cov.last_day:
            return SearchQueriesResponse(rows=[], total=0, last_day=None)
        span = _clamp_days(days if days is not None else (28 if view == "striking" else 90))
        normalised = self._normalised_pages(pages_in, "filtered")
        limit, offset = _page_bounds(limit, offset)
        rollup = await site_search_dailies.queries_rollup(
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
            rows=await self._enrich_queries(db, site_id, rollup),
            total=rollup.total,
            last_day=cov.last_day,
            days=span,
        )

    async def changes(
        self, db: AsyncSession, user_id: str, site_id: str, days: float | None = None
    ) -> SearchChangesResponse:
        await site_service.get(db, user_id, site_id)
        cov = await site_search_dailies.coverage(db, site_id)
        if not cov.last_day:
            return SearchChangesResponse(up=[], down=[], last_day=None, has_data=False)
        span = _clamp_days(days if days is not None else 90)
        result = await site_search_dailies.movers(db, site_id, cov.last_day, span)
        return SearchChangesResponse(
            up=result.up, down=result.down, last_day=cov.last_day, days=span, has_data=True
        )


site_search_service = SiteSearchService()
