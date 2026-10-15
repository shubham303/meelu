from datetime import UTC, datetime
from typing import Any

from sqlalchemy import cast, func, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.social_listening.models.run import SocialListeningRun
from src.social_listening.schemas import RunResponse


class SocialListeningRunRepository:
    ID_PREFIX = "slr"

    async def create(self, db: AsyncSession, user_id: str, site_id: str) -> RunResponse:
        now = datetime.now(UTC)
        row = SocialListeningRun(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            status="running",
            started_at=now,
            fetched_count=0,
            matched_count=0,
            kept_count=0,
            platform_stats={},
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return RunResponse.model_validate(row)

    async def running_for_user(self, db: AsyncSession, user_id: str) -> SocialListeningRun | None:
        result = await db.execute(
            select(SocialListeningRun)
            .where(SocialListeningRun.user_id == user_id, SocialListeningRun.status == "running")
            .limit(1)
        )
        return result.scalars().first()

    async def fail_running_before(
        self, db: AsyncSession, cutoff: datetime, message: str, user_id: str | None = None
    ) -> int:
        conds = [SocialListeningRun.status == "running", SocialListeningRun.started_at < cutoff]
        if user_id is not None:
            conds.append(SocialListeningRun.user_id == user_id)
        result = await db.execute(
            update(SocialListeningRun)
            .where(*conds)
            .values(status="error", error=message, finished_at=func.now(), updated_at=func.now())
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def merge_platform_stats(
        self,
        db: AsyncSession,
        run_id: str,
        platform: str,
        stats: dict[str, Any],
        fetched: int = 0,
    ) -> None:
        await db.execute(
            update(SocialListeningRun)
            .where(SocialListeningRun.id == run_id)
            .values(
                platform_stats=SocialListeningRun.platform_stats.op("||")(
                    func.jsonb_build_object(platform, cast(stats, JSONB))
                ),
                fetched_count=SocialListeningRun.fetched_count + fetched,
                updated_at=func.now(),
            )
        )
        await db.flush()

    async def get(self, db: AsyncSession, site_id: str, run_id: str) -> SocialListeningRun | None:
        result = await db.execute(
            select(SocialListeningRun)
            .where(SocialListeningRun.site_id == site_id, SocialListeningRun.id == run_id)
            .limit(1)
        )
        return result.scalars().first()

    async def latest(self, db: AsyncSession, site_id: str) -> RunResponse | None:
        result = await db.execute(
            select(SocialListeningRun)
            .where(SocialListeningRun.site_id == site_id)
            .order_by(SocialListeningRun.seq.desc())
            .limit(1)
        )
        row = result.scalars().first()
        return None if row is None else RunResponse.model_validate(row)

    async def update(
        self, db: AsyncSession, row: SocialListeningRun, values: dict[str, Any]
    ) -> RunResponse:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return RunResponse.model_validate(row)

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[RunResponse]:
        query = (
            select(SocialListeningRun)
            .where(SocialListeningRun.site_id == site_id)
            .order_by(SocialListeningRun.seq.desc())
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, RunResponse
        )


social_listening_runs = SocialListeningRunRepository()
