from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.site_traffic.schemas import (
    ContentSort,
    LandingSort,
    RollupKind,
    TrafficBreakdownResponse,
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
    TrafficSyncClaimResponse,
    TrafficSyncJobsResponse,
    TrafficSyncResponse,
    TrafficSyncStartRequest,
    TrafficSyncStartResponse,
    TrafficSyncUpdateRequest,
)
from src.seo.site_traffic.service import site_traffic_service

router = APIRouter()


@router.get("/site/traffic")
async def overview(
    days: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficOverviewResponse:
    return await site_traffic_service.overview(db, ctx.user_id, ctx.site_id, days)


@router.get("/site/traffic/property")
async def get_property(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficPropertyResponse:
    return await site_traffic_service.get_property(db, ctx.user_id, ctx.site_id)


@router.put("/site/traffic/property")
async def put_property(
    body: TrafficPropertyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficPropertyUpdateResponse:
    return await site_traffic_service.set_property(db, ctx.user_id, ctx.site_id, body)


@router.get("/site/traffic/rows")
async def export_rows(
    report: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficRowsExportResponse:
    return await site_traffic_service.export_rows(
        db, ctx.user_id, ctx.site_id, report=report, limit=limit, offset=offset
    )


@router.post("/site/traffic/rows")
async def ingest_rows(
    body: TrafficRowsIngestRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficRowsIngestResponse:
    return await site_traffic_service.ingest_rows(db, ctx.user_id, ctx.site_id, body)


@router.get("/site/traffic/series")
async def series(
    days: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficSeriesResponse:
    return await site_traffic_service.series(db, ctx.user_id, ctx.site_id, days)


@router.get("/site/traffic/pages")
async def landing_pages(
    days: int | None = Query(None),
    channel: str | None = Query(None),
    search: str | None = Query(None),
    sort: LandingSort | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficLandingPagesResponse:
    return await site_traffic_service.landing_pages(
        db,
        ctx.user_id,
        ctx.site_id,
        days=days,
        channel=channel,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/site/traffic/content")
async def content_pages(
    days: int | None = Query(None),
    search: str | None = Query(None),
    sort: ContentSort | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficContentPagesResponse:
    return await site_traffic_service.content_pages(
        db,
        ctx.user_id,
        ctx.site_id,
        days=days,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/site/traffic/breakdown")
async def breakdown(
    by: RollupKind = Query("channel"),
    days: int | None = Query(None),
    search: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficBreakdownResponse:
    return await site_traffic_service.breakdown(
        db,
        ctx.user_id,
        ctx.site_id,
        by=by,
        days=days,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/site/traffic/sync-jobs")
async def sync_jobs(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficSyncJobsResponse:
    return await site_traffic_service.sync_jobs(db, ctx.site_id)


@router.post("/site/traffic/sync-jobs")
async def start_sync(
    body: TrafficSyncStartRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficSyncStartResponse:
    started = await site_traffic_service.start_sync(db, ctx.user_id, ctx.site_id, body.trigger)
    response.status_code = 202 if started.started else 409
    return TrafficSyncStartResponse.model_validate(started)


@router.get("/site/traffic/sync-jobs/{id}")
async def get_sync(
    id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficSyncResponse:
    return TrafficSyncResponse.model_validate(
        await site_traffic_service.get_sync(db, ctx.site_id, id)
    )


@router.patch("/site/traffic/sync-jobs/{id}")
async def patch_sync(
    id: str,
    body: TrafficSyncUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficSyncResponse:
    record = await site_traffic_service.patch_sync(db, ctx.user_id, ctx.site_id, id, body)
    return TrafficSyncResponse.model_validate(record)


@router.post("/site/traffic/sync-jobs/{id}/claim")
async def claim_sync(
    id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrafficSyncClaimResponse:
    result = await site_traffic_service.claim_sync(db, ctx.user_id, ctx.site_id, id)
    return TrafficSyncClaimResponse.model_validate(result)
