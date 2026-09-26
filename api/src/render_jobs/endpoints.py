from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.render_jobs.schemas import (
    RENDER_DEVICES,
    PageRenderCreateRequest,
    PageRenderResponse,
    RenderJobBeatResponse,
    RenderJobClaimResponse,
    RenderJobOpenRequest,
    RenderJobReapRequest,
    RenderJobReapResponse,
    RenderJobResponse,
    RenderJobStartResponse,
    RenderJobStatusResponse,
    RenderJobUpdateRequest,
)
from src.render_jobs.service import STALE_JOB_MS, render_job_service

router = APIRouter()


def render_device(device: str = Query("desktop")) -> str:
    if device not in RENDER_DEVICES:
        raise HTTPException(400, f"device must be one of {', '.join(RENDER_DEVICES)}.")
    return device


@router.get("/site/render-jobs")
async def render_status(
    device: str = Depends(render_device),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RenderJobStatusResponse:
    return RenderJobStatusResponse(
        status=await render_job_service.status(db, ctx.user_id, ctx.site_id, device)
    )


@router.post("/site/render-jobs")
async def open_render_job(
    body: RenderJobOpenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RenderJobStartResponse:
    started = await render_job_service.start(db, ctx.user_id, ctx.site_id, body)
    response.status_code = 202 if started.started else 409
    return RenderJobStartResponse(
        started=started.started,
        job=None if started.job is None else RenderJobResponse.model_validate(started.job),
        reason=started.reason,
    )


@router.post("/site/render-jobs/reap")
async def reap_render_jobs(
    body: RenderJobReapRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RenderJobReapResponse:
    stale = body.stale_ms
    reaped = await render_job_service.reap(
        db,
        [ctx.site_id],
        stale if stale is not None else STALE_JOB_MS,
        reason=(
            "the process running it went away"
            if stale == 0
            else "no progress reported — the process running it is gone"
        ),
    )
    return RenderJobReapResponse(
        reaped=len(reaped), jobs=[RenderJobResponse.model_validate(j) for j in reaped]
    )


@router.patch("/site/render-jobs/{job_id}")
async def patch_render_job(
    job_id: str,
    body: RenderJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RenderJobResponse | RenderJobBeatResponse:
    status = body.status or ""

    if status == "cancelling":
        stopped = await render_job_service.stop(
            db, ctx.user_id, ctx.site_id, job_id, body.reason or "stopped by the user"
        )
        return RenderJobResponse.model_validate(stopped)
    if status == "running" or body.heartbeat is True:
        beat = await render_job_service.beat(db, ctx.site_id, job_id, body)
        return RenderJobBeatResponse(stop=beat.stop)
    if status in ("completed", "failed", "cancelled"):
        settled = await render_job_service.settle(db, ctx.user_id, ctx.site_id, job_id, body)
        return RenderJobResponse.model_validate(settled)

    raise HTTPException(
        400,
        f'Unknown status "{status}". A render reports progress with {{"heartbeat":true}}, '
        f'finishes with "completed", "failed" or "cancelled", and is stopped with "cancelling".',
    )


@router.post("/site/render-jobs/{job_id}/claim")
async def claim_render_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RenderJobClaimResponse:
    claimed = await render_job_service.claim(db, ctx.user_id, ctx.site_id, job_id)
    return RenderJobClaimResponse(
        job=RenderJobResponse.model_validate(claimed.job),
        target=claimed.target,
        pages=claimed.pages,
    )


@router.get("/site/page-renders")
async def get_page_render(
    page_id: str = Query(..., alias="pageId", min_length=1),
    device: str = Depends(render_device),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageRenderResponse:
    return PageRenderResponse.model_validate(
        await render_job_service.get_page_render(db, ctx.user_id, ctx.site_id, page_id, device)
    )


@router.post("/site/page-renders", status_code=201)
async def save_page_render(
    body: PageRenderCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageRenderResponse:
    saved = await render_job_service.save_page_render(db, ctx.user_id, ctx.site_id, body)
    return PageRenderResponse.model_validate(saved)


@router.delete("/site/page-renders", status_code=204)
async def delete_page_render(
    page_id: str = Query(..., alias="pageId", min_length=1),
    device: str = Depends(render_device),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> Response:
    await render_job_service.delete_page_render(db, ctx.user_id, ctx.site_id, page_id, device)
    return Response(status_code=204)
