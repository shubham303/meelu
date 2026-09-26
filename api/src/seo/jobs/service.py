from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.jobs.repository import seo_jobs
from src.seo.jobs.schemas import SeoJobRecord, SeoJobUpdateRequest

JOB_NOT_FOUND = "No such SEO job on this website."


class SeoJobService:
    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> SeoJobRecord:
        found = await seo_jobs.get(db, site_id, job_id)
        if found is None:
            raise HTTPException(404, JOB_NOT_FOUND)
        return found

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[SeoJobRecord]:
        return await seo_jobs.list(db, site_id, paging)

    async def finish(
        self, db: AsyncSession, site_id: str, job_id: str, body: SeoJobUpdateRequest
    ) -> SeoJobRecord:
        updated = await seo_jobs.update_status(db, site_id, job_id, body.status)
        if updated is None:
            raise HTTPException(404, JOB_NOT_FOUND)
        return updated


seo_job_service = SeoJobService()
