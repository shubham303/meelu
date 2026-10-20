from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.geo.models.check import GeoCheck
from src.geo.schemas import CheckResponse


class GeoCheckRepository:
    ID_PREFIX = "gec"

    async def create(self, db: AsyncSession, user_id: str, site_id: str, query_id: str) -> GeoCheck:
        now = datetime.now(UTC)
        row = GeoCheck(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            query_id=query_id,
            status="running",
            progress={},
            started_at=now,
            required_points=[],
            pages=[],
            ai_answers=[],
            page_adds=[],
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    async def get(self, db: AsyncSession, site_id: str, check_id: str) -> GeoCheck | None:
        result = await db.execute(
            select(GeoCheck).where(GeoCheck.site_id == site_id, GeoCheck.id == check_id).limit(1)
        )
        return result.scalars().first()

    async def get_by_id(self, db: AsyncSession, check_id: str) -> GeoCheck | None:
        result = await db.execute(select(GeoCheck).where(GeoCheck.id == check_id).limit(1))
        return result.scalars().first()

    async def running_query_ids(self, db: AsyncSession, site_id: str) -> set[str]:
        result = await db.execute(
            select(GeoCheck.query_id).where(
                GeoCheck.site_id == site_id, GeoCheck.status == "running"
            )
        )
        return set(result.scalars().all())

    async def latest_by_query(self, db: AsyncSession, site_id: str) -> dict[str, GeoCheck]:
        result = await db.execute(
            select(GeoCheck)
            .where(GeoCheck.site_id == site_id)
            .distinct(GeoCheck.query_id)
            .order_by(GeoCheck.query_id, GeoCheck.seq.desc())
        )
        return {row.query_id: row for row in result.scalars().all()}

    async def latest_finished_by_query(self, db: AsyncSession, site_id: str) -> dict[str, GeoCheck]:
        result = await db.execute(
            select(GeoCheck)
            .where(GeoCheck.site_id == site_id, GeoCheck.status == "done")
            .distinct(GeoCheck.query_id)
            .order_by(GeoCheck.query_id, GeoCheck.seq.desc())
        )
        return {row.query_id: row for row in result.scalars().all()}

    async def list_for_query(
        self, db: AsyncSession, site_id: str, query_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[CheckResponse]:
        query = (
            select(GeoCheck)
            .where(GeoCheck.site_id == site_id, GeoCheck.query_id == query_id)
            .order_by(GeoCheck.seq.desc())
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, CheckResponse
        )

    async def update(self, db: AsyncSession, check_id: str, values: dict[str, Any]) -> None:
        await db.execute(
            update(GeoCheck).where(GeoCheck.id == check_id).values(**values, updated_at=func.now())
        )
        await db.flush()

    async def finish_running(self, db: AsyncSession, check_id: str, values: dict[str, Any]) -> None:
        await db.execute(
            update(GeoCheck)
            .where(GeoCheck.id == check_id, GeoCheck.status == "running")
            .values(**values, updated_at=func.now())
        )
        await db.flush()

    async def stop_running(self, db: AsyncSession, site_id: str) -> list[str]:
        result = await db.execute(
            update(GeoCheck)
            .where(GeoCheck.site_id == site_id, GeoCheck.status == "running")
            .values(status="stopped", finished_at=func.now(), updated_at=func.now())
            .returning(GeoCheck.id)
        )
        await db.flush()
        return list(result.scalars().all())

    async def fail_running_before(self, db: AsyncSession, cutoff: datetime, message: str) -> int:
        result = await db.execute(
            update(GeoCheck)
            .where(GeoCheck.status == "running", GeoCheck.started_at < cutoff)
            .values(status="error", error=message, finished_at=func.now(), updated_at=func.now())
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def delete(self, db: AsyncSession, row: GeoCheck) -> None:
        await db.delete(row)
        await db.flush()


geo_checks = GeoCheckRepository()
