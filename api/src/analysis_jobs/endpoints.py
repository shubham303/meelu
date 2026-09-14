from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.analysis_jobs import service
from src.analysis_jobs.schemas import (
    AnalysisJobBeatResponse,
    AnalysisJobClaimResponse,
    AnalysisJobOpenRequest,
    AnalysisJobReapRequest,
    AnalysisJobReapResponse,
    AnalysisJobResponse,
    AnalysisJobStartResponse,
    AnalysisJobStatusResponse,
    AnalysisJobUpdateRequest,
    PageAnalysisCreateRequest,
    PageAnalysisResponse,
)
from src.auth import AuthContext, require_site
from src.core.database import get_db

router = APIRouter()


@router.get("/site/analysis-jobs")
async def analysis_status(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalysisJobStatusResponse:
    return AnalysisJobStatusResponse(
        status=await service.analysis_status(db, ctx.user_id, ctx.site_id)
    )


@router.post("/site/analysis-jobs")
async def open_analysis_job(
    body: AnalysisJobOpenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalysisJobStartResponse:
    started = await service.start_analysis(db, ctx.user_id, ctx.site_id, body.trigger)
    response.status_code = 202 if started.started else 409
    return AnalysisJobStartResponse(
        started=started.started,
        job=None if started.job is None else AnalysisJobResponse.model_validate(started.job),
        reason=started.reason,
    )


@router.post("/site/analysis-jobs/reap")
async def reap_analysis_jobs(
    body: AnalysisJobReapRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalysisJobReapResponse:
    stale = body.stale_ms
    reaped = await service.reap_analyses(
        db,
        [ctx.site_id],
        stale if stale is not None else service.STALE_JOB_MS,
        reason=(
            "the process running it went away"
            if stale == 0
            else "no progress reported — the process running it is gone"
        ),
    )
    return AnalysisJobReapResponse(
        reaped=len(reaped), jobs=[AnalysisJobResponse.model_validate(j) for j in reaped]
    )


@router.patch("/site/analysis-jobs/{job_id}")
async def patch_analysis_job(
    job_id: str,
    body: AnalysisJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalysisJobResponse | AnalysisJobBeatResponse:
    status = body.status or ""

    if status == "cancelling":
        stopped = await service.stop_analysis(
            db, ctx.user_id, ctx.site_id, job_id, body.reason or "stopped by the user"
        )
        return AnalysisJobResponse.model_validate(stopped)
    if status == "running" or body.heartbeat is True:
        beat = await service.beat_analysis(db, ctx.site_id, job_id, body)
        return AnalysisJobBeatResponse(stop=beat.stop)
    if status in ("completed", "failed", "cancelled"):
        settled = await service.settle_analysis(db, ctx.user_id, ctx.site_id, job_id, body)
        return AnalysisJobResponse.model_validate(settled)

    raise HTTPException(
        400,
        f'Unknown status "{status}". An analysis reports progress with {{"heartbeat":true}}, '
        f'finishes with "completed", "failed" or "cancelled", and is stopped with "cancelling".',
    )


@router.post("/site/analysis-jobs/{job_id}/claim")
async def claim_analysis_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalysisJobClaimResponse:
    claimed = await service.claim_analysis(db, ctx.user_id, ctx.site_id, job_id)
    return AnalysisJobClaimResponse(
        job=AnalysisJobResponse.model_validate(claimed.job),
        target=claimed.target,
        pages=claimed.pages,
    )


@router.get("/site/page-analysis")
async def get_page_analysis(
    page_id: str = Query(..., alias="pageId", min_length=1),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageAnalysisResponse:
    return PageAnalysisResponse.model_validate(
        await service.read_page_analysis(db, ctx.user_id, ctx.site_id, page_id)
    )


@router.post("/site/page-analysis", status_code=201)
async def save_page_analysis(
    body: PageAnalysisCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageAnalysisResponse:
    saved = await service.save_page_analysis(db, ctx.user_id, ctx.site_id, body)
    return PageAnalysisResponse.model_validate(saved)
