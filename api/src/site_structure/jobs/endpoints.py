from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.site_structure.jobs.schemas import (
    StructureJobCreateRequest,
    StructureJobRecord,
    StructureJobUpdateRequest,
)
from src.site_structure.jobs.service import structure_job_service

router = APIRouter(prefix="/jobs")


@router.post("", status_code=201)
async def start_job(
    body: StructureJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StructureJobRecord:
    return await structure_job_service.create(db, ctx.user_id, ctx.site_id, body)


@router.get("")
async def list_jobs(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[StructureJobRecord]:
    return await structure_job_service.list(db, ctx.site_id, paging)


@router.get("/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StructureJobRecord:
    return await structure_job_service.get(db, ctx.site_id, job_id)


@router.patch("/{job_id}")
async def finish_job(
    job_id: str,
    body: StructureJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StructureJobRecord:
    return await structure_job_service.finish(db, ctx.site_id, job_id, body)
