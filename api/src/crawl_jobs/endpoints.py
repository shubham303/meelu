from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, any_site, require_site
from src.core.database import get_db
from src.core.pagination import PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.crawl_jobs import service
from src.crawl_jobs.schemas import (
    CRAWL_JOB_STATUSES,
    SETTLED_JOB_STATUSES,
    CrawlJobCreateRequest,
    CrawlJobDeleteResponse,
    CrawlJobFilters,
    CrawlJobHeartbeatResponse,
    CrawlJobListItemResponse,
    CrawlJobListResponse,
    CrawlJobReapRequest,
    CrawlJobReapResponse,
    CrawlJobResponse,
    CrawlJobSort,
    CrawlJobStartResponse,
    CrawlJobUpdateRequest,
    CrawlPlanResponse,
)

router = APIRouter()


@router.get("/site/crawl-jobs")
async def list_crawl_jobs(
    status: list[str] | None = Query(None),
    trigger: str | None = Query(None),
    active: bool | None = Query(None),
    complete: bool | None = Query(None),
    failed: bool | None = Query(None),
    started_after: datetime | None = Query(None, alias="startedAfter"),
    started_before: datetime | None = Query(None, alias="startedBefore"),
    finished_after: datetime | None = Query(None, alias="finishedAfter"),
    finished_before: datetime | None = Query(None, alias="finishedBefore"),
    created_after: datetime | None = Query(None, alias="createdAfter"),
    created_before: datetime | None = Query(None, alias="createdBefore"),
    sort: CrawlJobSort | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> CrawlJobListResponse:
    statuses = [s for s in status if s in CRAWL_JOB_STATUSES] if status else None
    filters = CrawlJobFilters(
        statuses=statuses or None,
        trigger=trigger,
        active=active,
        complete=complete,
        failed=failed,
        started_after=started_after,
        started_before=started_before,
        finished_after=finished_after,
        finished_before=finished_before,
        created_after=created_after,
        created_before=created_before,
        sort=sort,
    )
    page = await service.list_crawls(db, ctx.site_id, filters, paging)
    return CrawlJobListResponse(
        data=[CrawlJobListItemResponse.model_validate(j) for j in page.data],
        pagination=page.pagination,
        status=await service.crawl_status(db, ctx.user_id, ctx.site_id),
    )


@router.post("/site/crawl-jobs")
async def open_crawl_job(
    body: CrawlJobCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CrawlJobStartResponse:
    started = await service.start_crawl(db, ctx.user_id, ctx.site_id, body)
    response.status_code = 202 if started.started else 409
    return started


@router.post("/site/crawl-jobs/reap")
async def reap_crawl_jobs(
    body: CrawlJobReapRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
) -> CrawlJobReapResponse:
    stale = body.stale_ms
    reaped = await service.reap_crawls(
        db,
        [ctx.site_id],
        stale if stale is not None and (stale == 0 or stale >= 60_000) else service.STALE_JOB_MS,
        reason=(
            "the process running it went away"
            if stale == 0
            else "no progress reported — the process running it is gone"
        ),
    )
    return CrawlJobReapResponse(
        reaped=len(reaped),
        jobs=[CrawlJobResponse.model_validate(j) for j in reaped],
        note=(
            "These crawls had stopped reporting and were cleared. The website is free "
            "to crawl again — start a new one and it resumes where the dead run left "
            "off rather than from the first page."
            if reaped
            else "Nothing was stuck. Any crawl running for this website is still "
            "reporting progress."
        ),
    )


@router.get("/site/crawl-jobs/{job_id}")
async def get_crawl_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
) -> CrawlJobResponse:
    return CrawlJobResponse.model_validate(await service.read_crawl(db, ctx.site_id, job_id))


@router.patch("/site/crawl-jobs/{job_id}")
async def patch_crawl_job(
    job_id: str,
    body: CrawlJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
) -> CrawlJobResponse | CrawlJobHeartbeatResponse:
    status = body.status or ""

    if status == "cancelling":
        stopped = await service.stop_crawl(
            db,
            ctx.user_id,
            ctx.site_id,
            job_id=job_id,
            reason=body.reason or "stopped by the user",
        )
        return CrawlJobResponse.model_validate(stopped)
    if status == "running" or body.heartbeat is True:
        return await service.beat_crawl(db, ctx.site_id, job_id, body)
    if status in SETTLED_JOB_STATUSES:
        settled = await service.settle_crawl(db, ctx.user_id, ctx.site_id, job_id, body)
        return CrawlJobResponse.model_validate(settled)

    raise HTTPException(
        400,
        f'Unknown status "{status}". A crawl reports progress with {{"heartbeat":true}}, '
        f'finishes with "completed", "cancelled" or "failed", and is asked to stop '
        f'with "cancelling".',
    )


@router.delete("/site/crawl-jobs/{job_id}")
async def delete_crawl_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
) -> CrawlJobDeleteResponse:
    return await service.remove_crawl(db, ctx.user_id, ctx.site_id, job_id)


@router.post("/site/crawl-jobs/{job_id}/claim")
async def claim_crawl_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
) -> CrawlPlanResponse:
    return await service.claim_crawl(db, ctx.user_id, ctx.site_id, job_id)
