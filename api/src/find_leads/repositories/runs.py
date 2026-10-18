from datetime import UTC, datetime
from typing import Any

from sqlalchemy import cast, func, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.find_leads.models.run import LeadRun
from src.find_leads.schemas import RunResponse


class LeadRunRepository:
    ID_PREFIX = "lr"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, target_count: int
    ) -> RunResponse:
        now = datetime.now(UTC)
        row = LeadRun(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            status="running",
            target_count=target_count,
            round=0,
            started_at=now,
            found_count=0,
            shortlisted_count=0,
            kept_count=0,
            source_stats={},
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return RunResponse.model_validate(row)

    async def get(self, db: AsyncSession, site_id: str, run_id: str) -> LeadRun | None:
        result = await db.execute(
            select(LeadRun).where(LeadRun.site_id == site_id, LeadRun.id == run_id).limit(1)
        )
        return result.scalars().first()

    async def running_for_user(self, db: AsyncSession, user_id: str) -> LeadRun | None:
        result = await db.execute(
            select(LeadRun).where(LeadRun.user_id == user_id, LeadRun.status == "running").limit(1)
        )
        return result.scalars().first()

    async def fail_running_before(
        self, db: AsyncSession, cutoff: datetime, message: str, user_id: str | None = None
    ) -> int:
        conds = [LeadRun.status == "running", LeadRun.started_at < cutoff]
        if user_id is not None:
            conds.append(LeadRun.user_id == user_id)
        result = await db.execute(
            update(LeadRun)
            .where(*conds)
            .values(status="error", error=message, finished_at=func.now(), updated_at=func.now())
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def merge_source_stats(
        self, db: AsyncSession, run_id: str, key: str, stats: dict[str, Any], found: int = 0
    ) -> None:
        await db.execute(
            update(LeadRun)
            .where(LeadRun.id == run_id)
            .values(
                source_stats=LeadRun.source_stats.op("||")(
                    func.jsonb_build_object(key, cast(stats, JSONB))
                ),
                found_count=LeadRun.found_count + found,
                updated_at=func.now(),
            )
        )
        await db.flush()

    async def latest(self, db: AsyncSession, site_id: str) -> RunResponse | None:
        result = await db.execute(
            select(LeadRun).where(LeadRun.site_id == site_id).order_by(LeadRun.seq.desc()).limit(1)
        )
        row = result.scalars().first()
        return None if row is None else RunResponse.model_validate(row)

    async def update(self, db: AsyncSession, row: LeadRun, values: dict[str, Any]) -> RunResponse:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return RunResponse.model_validate(row)

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[RunResponse]:
        query = select(LeadRun).where(LeadRun.site_id == site_id).order_by(LeadRun.seq.desc())
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, RunResponse
        )


lead_runs = LeadRunRepository()
