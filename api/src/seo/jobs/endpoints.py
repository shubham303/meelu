from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.seo.jobs.schemas import SeoJobCreateRequest, SeoJobRecord, SeoJobUpdateRequest
from src.seo.jobs.service import seo_job_service
from src.seo.pipeline.schemas import ReconcileResult
from src.seo.service import seo_service

router = APIRouter()


class StartedJobResponse(SeoJobRecord):
    reconciled: ReconcileResult


@router.post("/jobs", status_code=201)
async def start_job(
    body: SeoJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StartedJobResponse:
    job, reconciled = await seo_service.start_job(db, ctx.user_id, ctx.site_id, body)
    return StartedJobResponse(**job.model_dump(), reconciled=reconciled)


@router.get("/jobs")
async def list_jobs(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[SeoJobRecord]:
    return await seo_job_service.list(db, ctx.site_id, paging)


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str, db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> SeoJobRecord:
    return await seo_job_service.get(db, ctx.site_id, job_id)


@router.patch("/jobs/{job_id}")
async def finish_job(
    job_id: str,
    body: SeoJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SeoJobRecord:
    return await seo_job_service.finish(db, ctx.site_id, job_id, body)
