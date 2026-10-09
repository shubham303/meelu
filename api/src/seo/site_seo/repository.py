from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_seo.constants import SITE_SEO_ID_PREFIX
from src.seo.site_seo.models.site_seo import SiteSeo


class SiteSeoRepository:
    async def backlink_opportunities(self, db: AsyncSession, site_id: str) -> list[str]:
        found = await db.scalar(
            select(SiteSeo.backlink_opportunities).where(SiteSeo.site_id == site_id)
        )
        return list(found or [])

    async def set_backlink_opportunities(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[str]
    ) -> list[str]:
        now = datetime.now(UTC)
        statement = insert(SiteSeo).values(
            id=uid(SITE_SEO_ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            created_at=now,
            updated_at=now,
            backlink_opportunities=items,
        )
        saved = await db.scalar(
            statement.on_conflict_do_update(
                index_elements=["site_id"],
                set_={"backlink_opportunities": items, "updated_at": now},
            ).returning(SiteSeo.backlink_opportunities)
        )
        return list(saved or [])


site_seo = SiteSeoRepository()
