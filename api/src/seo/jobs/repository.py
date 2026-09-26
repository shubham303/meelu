from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.common.repository import now, page
from src.seo.jobs.model import SeoJob
from src.seo.jobs.schemas import SeoJobRecord


class SeoJobRepository:
    ID_PREFIX = "sjob"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, prompt: str, ceiling: int
    ) -> SeoJobRecord:
        at = now()
        row = SeoJob(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            prompt=prompt,
            status="RUNNING",
            vendor_ceiling_micros=ceiling,
            created_at=at,
            updated_at=at,
        )
        db.add(row)
        await db.flush()
        return SeoJobRecord.model_validate(row)

    async def fail_running(self, db: AsyncSession, site_id: str) -> int:
        result = await db.execute(
            update(SeoJob)
            .where(SeoJob.site_id == site_id, SeoJob.status == "RUNNING")
            .values(status="FAILED", updated_at=now())
        )
        return result.rowcount or 0

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> SeoJobRecord | None:
        row = (
            await db.execute(select(SeoJob).where(SeoJob.site_id == site_id, SeoJob.id == job_id))
        ).scalar_one_or_none()
        return None if row is None else SeoJobRecord.model_validate(row)

    async def update_status(
        self, db: AsyncSession, site_id: str, job_id: str, status: str
    ) -> SeoJobRecord | None:
        await db.execute(
            update(SeoJob)
            .where(SeoJob.site_id == site_id, SeoJob.id == job_id)
            .values(status=status, updated_at=now())
        )
        return await self.get(db, site_id, job_id)

    async def add_spend(self, db: AsyncSession, job_id: str, calls: int, micros: int) -> None:
        await db.execute(
            update(SeoJob)
            .where(SeoJob.id == job_id)
            .values(
                vendor_calls=SeoJob.vendor_calls + calls,
                vendor_micros=SeoJob.vendor_micros + micros,
                updated_at=now(),
            )
        )

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[SeoJobRecord]:
        query = select(SeoJob).where(SeoJob.site_id == site_id)
        return await page(db, query, SeoJob.seq.desc(), paging, SeoJobRecord)


seo_jobs = SeoJobRepository()
