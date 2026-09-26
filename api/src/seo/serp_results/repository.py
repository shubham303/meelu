from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.serp_results.model import SeoSerpResult
from src.seo.serp_results.schemas import SerpResultRecord


class SeoSerpResultRepository:
    ID_PREFIX = "srp"

    async def create_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        snapshot_id: str,
        at: datetime,
        results: list[dict[str, Any]],
    ) -> None:
        for r in results:
            db.add(
                SeoSerpResult(
                    id=uid(self.ID_PREFIX),
                    user_id=user_id,
                    site_id=site_id,
                    snapshot_id=snapshot_id,
                    created_at=at,
                    updated_at=at,
                    **r,
                )
            )
        await db.flush()

    async def top_for_snapshot(
        self, db: AsyncSession, snapshot_id: str, limit: int
    ) -> list[SerpResultRecord]:
        rows = (
            await db.execute(
                select(SeoSerpResult)
                .where(SeoSerpResult.snapshot_id == snapshot_id)
                .order_by(SeoSerpResult.rank)
                .limit(limit)
            )
        ).scalars()
        return [SerpResultRecord.model_validate(r) for r in rows]

    async def list_by_snapshot_ids(
        self, db: AsyncSession, snapshot_ids: list[str]
    ) -> list[SerpResultRecord]:
        if not snapshot_ids:
            return []
        rows = (
            await db.execute(
                select(SeoSerpResult)
                .where(SeoSerpResult.snapshot_id.in_(set(snapshot_ids)))
                .order_by(SeoSerpResult.rank)
            )
        ).scalars()
        return [SerpResultRecord.model_validate(r) for r in rows]


seo_serp_results = SeoSerpResultRepository()
