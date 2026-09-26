from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_structure.jobs.schemas import JobStatus, StructureJobRecord
from src.site_structure.models.structure_job import StructureJob


class StructureJobRepository:
    ID_PREFIX = "sjb"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, prompt: str
    ) -> StructureJobRecord:
        now = datetime.now(UTC)
        row = StructureJob(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            prompt=prompt,
            status=JobStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return StructureJobRecord.model_validate(row)

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord | None:
        row = await self._row(db, site_id, job_id)
        return None if row is None else StructureJobRecord.model_validate(row)

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[StructureJobRecord]:
        query = (
            select(StructureJob)
            .where(StructureJob.site_id == site_id)
            .order_by(StructureJob.seq.desc())
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, StructureJobRecord
        )

    async def set_status(
        self, db: AsyncSession, site_id: str, job_id: str, status: JobStatus
    ) -> StructureJobRecord | None:
        row = await self._row(db, site_id, job_id)
        if row is None:
            return None
        row.status = status
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return StructureJobRecord.model_validate(row)

    async def fail_running_before(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(
            update(StructureJob)
            .where(
                StructureJob.status == JobStatus.RUNNING,
                StructureJob.created_at < cutoff,
            )
            .values(status=JobStatus.FAILED, updated_at=datetime.now(UTC))
        )
        return result.rowcount or 0

    async def _row(self, db: AsyncSession, site_id: str, job_id: str) -> StructureJob | None:
        return (
            await db.execute(
                select(StructureJob).where(
                    StructureJob.site_id == site_id, StructureJob.id == job_id
                )
            )
        ).scalar_one_or_none()


structure_jobs = StructureJobRepository()
