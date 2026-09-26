from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.common.repository import now
from src.seo.state.model import SeoSiteState
from src.seo.state.schemas import SiteStateRecord


class SeoSiteStateRepository:
    ID_PREFIX = "sst"

    async def get(self, db: AsyncSession, site_id: str) -> SiteStateRecord | None:
        row = (
            await db.execute(select(SeoSiteState).where(SeoSiteState.site_id == site_id))
        ).scalar_one_or_none()
        return None if row is None else SiteStateRecord.model_validate(row)

    async def ensure(self, db: AsyncSession, user_id: str, site_id: str) -> SiteStateRecord:
        at = now()
        await db.execute(
            insert(SeoSiteState)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                created_at=at,
                updated_at=at,
            )
            .on_conflict_do_nothing(index_elements=["site_id"])
        )
        await db.flush()
        found = await self.get(db, site_id)
        assert found is not None
        return found

    async def patch(self, db: AsyncSession, site_id: str, patch: dict[str, Any]) -> SiteStateRecord:
        await db.execute(
            update(SeoSiteState)
            .where(SeoSiteState.site_id == site_id)
            .values(**patch, updated_at=now())
        )
        await db.flush()
        found = await self.get(db, site_id)
        assert found is not None
        return found

    async def request_precompute(self, db: AsyncSession, site_id: str) -> None:
        await db.execute(
            update(SeoSiteState)
            .where(SeoSiteState.site_id == site_id)
            .values(precompute_requested_at=func.now(), updated_at=func.now())
        )

    async def mark_rollup(
        self, db: AsyncSession, site_id: str, at: datetime, curve: dict[str, float]
    ) -> None:
        await db.execute(
            update(SeoSiteState)
            .where(SeoSiteState.site_id == site_id)
            .values(rollup_at=at, ctr_curve=curve, updated_at=at)
        )

    async def mark_embedded(self, db: AsyncSession, site_id: str) -> None:
        await db.execute(
            update(SeoSiteState)
            .where(SeoSiteState.site_id == site_id)
            .values(embedded_at=func.now(), updated_at=func.now())
        )

    async def list_awaiting_embedding(self, db: AsyncSession) -> list[tuple[str, str]]:
        rows = await db.execute(
            select(SeoSiteState.site_id, SeoSiteState.user_id).where(
                SeoSiteState.precompute_requested_at
                > func.coalesce(SeoSiteState.embedded_at, text("'-infinity'::timestamptz"))
            )
        )
        return [(site_id, user_id) for site_id, user_id in rows.tuples()]


seo_site_states = SeoSiteStateRepository()
