from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
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
            kept_count=0,
            platform_stats={},
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return RunResponse.model_validate(row)

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
