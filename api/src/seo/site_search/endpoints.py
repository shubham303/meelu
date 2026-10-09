from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.site_search.schemas import (
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
    SearchSeriesResponse,
    SearchSyncClaimResponse,
    SearchSyncJobsResponse,
    SearchSyncResponse,
    SearchSyncStartRequest,
    SearchSyncStartResponse,
    SearchSyncUpdateRequest,
)
from src.seo.site_search.service import site_search_service

router = APIRouter()

PageSort = Literal[
    "clicks", "delta", "impressions", "ctr", "position", "page", "index", "crawled", "inspected"
]


def _split_pages(raw: str | None) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def _positive(days: float | None) -> float | None:
    return days if days is not None and days > 0 else None


@router.get("/site/search-data")
async def overview(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchOverviewResponse:
    return await site_search_service.overview(db, ctx.user_id, ctx.site_id)


@router.post("/site/search-data/property")
async def set_property(
    body: SearchPropertyRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchPropertyResponse:
    return await site_search_service.set_property(db, ctx.user_id, ctx.site_id, body)


@router.post("/site/search-data/rows")
async def ingest_rows(
    body: SearchRowsIngestRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchRowsIngestResponse:
    return await site_search_service.ingest_days(db, ctx.user_id, ctx.site_id, body)


@router.get("/site/search-data/queries")
async def queries(
    view: str | None = Query(None),
    days: float | None = Query(None),
    pages: str | None = Query(None),
    search: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchQueriesResponse:
    return await site_search_service.queries(
        db,
        ctx.user_id,
        ctx.site_id,
        view="striking" if view == "striking" else "top",
        days=days,
        pages_in=_split_pages(pages),
        search=search or None,
        limit=limit,
        offset=offset,
    )


@router.get("/site/search-data/pages")
async def pages(
    url: str | None = Query(None),
    days: float | None = Query(None),
    sort: PageSort = Query("clicks"),
    dir: Literal["asc", "desc"] | None = Query(None),
    search: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchPagesResponse | SearchPageDetailResponse:
    if url:
        return await site_search_service.page_detail(db, ctx.user_id, ctx.site_id, url, days)
    return await site_search_service.pages(
        db,
        ctx.user_id,
        ctx.site_id,
        days=days,
        sort=sort,
        dir=dir,
        search=search or None,
        limit=limit,
        offset=offset,
    )


@router.get("/site/search-data/series")
async def series(
    days: float | None = Query(None),
    pages: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchSeriesResponse:
    return await site_search_service.series(
        db, ctx.user_id, ctx.site_id, days=_positive(days), pages=_split_pages(pages)
    )


@router.get("/site/search-data/changes")
async def changes(
    days: float | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchChangesResponse:
    return await site_search_service.changes(db, ctx.user_id, ctx.site_id, _positive(days))


@router.get("/site/search-data/inspections")
async def inspection_targets(
    limit: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchInspectionTargetsResponse:
    return await site_search_service.inspection_targets(db, ctx.user_id, ctx.site_id, limit)


@router.post("/site/search-data/inspections")
async def ingest_inspections(
    body: SearchInspectionsIngestRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchInspectionsIngestResponse:
    return await site_search_service.ingest_inspections(db, ctx.user_id, ctx.site_id, body)


@router.get("/site/search-data/sync-jobs")
async def sync_jobs(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchSyncJobsResponse:
    return await site_search_service.sync_jobs(db, ctx.user_id, ctx.site_id)


@router.post("/site/search-data/sync-jobs")
async def start_sync(
    response: Response,
    body: SearchSyncStartRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchSyncStartResponse:
    trigger = body.trigger if body is not None else "user"
    started = await site_search_service.start_sync(db, ctx.user_id, ctx.site_id, trigger)
    response.status_code = 202 if started.started else 409
    return started


@router.get("/site/search-data/sync-jobs/{id}")
async def get_sync(
    id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchSyncResponse:
    record = await site_search_service.get_sync(db, ctx.user_id, ctx.site_id, id)
    return SearchSyncResponse.model_validate(record)


@router.patch("/site/search-data/sync-jobs/{id}")
async def patch_sync(
    id: str,
    body: SearchSyncUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchSyncResponse:
    record = await site_search_service.patch_sync(db, ctx.user_id, ctx.site_id, id, body)
    return SearchSyncResponse.model_validate(record)


@router.post("/site/search-data/sync-jobs/{id}/claim")
async def claim_sync(
    id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchSyncClaimResponse:
    return await site_search_service.claim_sync(db, ctx.user_id, ctx.site_id, id)
