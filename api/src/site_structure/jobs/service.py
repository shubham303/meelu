from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_structure.jobs.repository import structure_jobs
from src.site_structure.jobs.schemas import (
    StructureJobCreateRequest,
    StructureJobRecord,
    StructureJobUpdateRequest,
)

STALE_AFTER = timedelta(hours=1)

NOT_FOUND = "No such structure job on this website."


class StructureJobService:
    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, body: StructureJobCreateRequest
    ) -> StructureJobRecord:
        return await structure_jobs.create(db, user_id, site_id, body.prompt)

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord:
        found = await structure_jobs.get(db, site_id, job_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        return found

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[StructureJobRecord]:
        return await structure_jobs.list(db, site_id, paging)

    async def finish(
        self, db: AsyncSession, site_id: str, job_id: str, body: StructureJobUpdateRequest
    ) -> StructureJobRecord:
        updated = await structure_jobs.set_status(db, site_id, job_id, body.status)
        if updated is None:
            raise HTTPException(404, NOT_FOUND)
        return updated

    async def fail_stale_jobs(self, db: AsyncSession) -> int:
        return await structure_jobs.fail_running_before(db, datetime.now(UTC) - STALE_AFTER)


structure_job_service = StructureJobService()
