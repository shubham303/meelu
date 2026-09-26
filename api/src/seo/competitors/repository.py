from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.common.repository import count, now
from src.seo.competitors.model import SeoCompetitor
from src.seo.competitors.schemas import CompetitorRecord


class SeoCompetitorRepository:
    ID_PREFIX = "cmp"

    async def get(
        self, db: AsyncSession, site_id: str, competitor_id: str
    ) -> CompetitorRecord | None:
        row = (
            await db.execute(
                select(SeoCompetitor).where(
                    SeoCompetitor.site_id == site_id, SeoCompetitor.id == competitor_id
                )
            )
        ).scalar_one_or_none()
        return None if row is None else CompetitorRecord.model_validate(row)

    async def patch(
        self, db: AsyncSession, site_id: str, competitor_id: str, patch: dict[str, Any]
    ) -> CompetitorRecord | None:
        await db.execute(
            update(SeoCompetitor)
            .where(SeoCompetitor.site_id == site_id, SeoCompetitor.id == competitor_id)
            .values(**patch, updated_at=now())
        )
        return await self.get(db, site_id, competitor_id)

    async def upsert(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> CompetitorRecord:
        at = now()
        stmt = (
            insert(SeoCompetitor)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                created_at=at,
                updated_at=at,
                **values,
            )
            .on_conflict_do_update(
                index_elements=["site_id", "domain"],
                set_={
                    "intersections": values.get("intersections"),
                    "avg_position": values.get("avg_position"),
                    "fetched_at": values.get("fetched_at"),
                    "updated_at": at,
                },
            )
            .returning(SeoCompetitor)
        )
        row = (await db.execute(stmt)).scalar_one()
        return CompetitorRecord.model_validate(row)

    async def count(self, db: AsyncSession, site_id: str, state: str | None = None) -> int:
        query = select(SeoCompetitor).where(SeoCompetitor.site_id == site_id)
        if state:
            query = query.where(SeoCompetitor.state == state)
        return await count(db, query)

    async def list(
        self, db: AsyncSession, site_id: str, state: str | None
    ) -> list[CompetitorRecord]:
        query = select(SeoCompetitor).where(SeoCompetitor.site_id == site_id)
        if state:
            query = query.where(SeoCompetitor.state == state)
        rows = (
            await db.execute(query.order_by(SeoCompetitor.intersections.desc().nulls_last()))
        ).scalars()
        return [CompetitorRecord.model_validate(r) for r in rows]


seo_competitors = SeoCompetitorRepository()
