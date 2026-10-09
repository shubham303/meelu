from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_seo.constants import COMPETITOR_ID_PREFIX
from src.seo.site_seo.models.seo_competitor import SeoCompetitor
from src.seo.site_seo.schemas import CompetitorRecord


class CompetitorRepository:
    async def list(self, db: AsyncSession, site_id: str) -> list[CompetitorRecord]:
        rows = await db.scalars(
            select(SeoCompetitor)
            .where(SeoCompetitor.site_id == site_id)
            .order_by(SeoCompetitor.seq)
        )
        return [CompetitorRecord.model_validate(r) for r in rows]

    async def add_many(
        self, db: AsyncSession, user_id: str, site_id: str, domains: list[str]
    ) -> list[str]:
        if not domains:
            return []
        now = datetime.now(UTC)
        statement = insert(SeoCompetitor).values(
            [
                {
                    "id": uid(COMPETITOR_ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "domain": domain,
                    "created_at": now,
                    "updated_at": now,
                }
                for domain in domains
            ]
        )
        added = await db.scalars(
            statement.on_conflict_do_nothing(index_elements=["site_id", "domain"]).returning(
                SeoCompetitor.domain
            )
        )
        return list(added)

    async def delete_domains(self, db: AsyncSession, site_id: str, domains: list[str]) -> list[str]:
        if not domains:
            return []
        removed = await db.scalars(
            delete(SeoCompetitor)
            .where(SeoCompetitor.site_id == site_id, SeoCompetitor.domain.in_(domains))
            .returning(SeoCompetitor.domain)
        )
        return list(removed)


seo_competitors = CompetitorRepository()
