from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_seo.constants import COMPETITOR_ID_PREFIX
from src.seo.site_seo.models.site_competitor import SiteCompetitor
from src.seo.site_seo.schemas import CompetitorRecord


class CompetitorRepository:
    async def list(self, db: AsyncSession, site_id: str) -> list[CompetitorRecord]:
        rows = await db.scalars(
            select(SiteCompetitor)
            .where(SiteCompetitor.site_id == site_id)
            .order_by(SiteCompetitor.seq)
        )
        return [CompetitorRecord.model_validate(r) for r in rows]

    async def get(
        self, db: AsyncSession, site_id: str, competitor_id: str
    ) -> CompetitorRecord | None:
        row = await db.scalar(
            select(SiteCompetitor).where(
                SiteCompetitor.site_id == site_id, SiteCompetitor.id == competitor_id
            )
        )
        return None if row is None else CompetitorRecord.model_validate(row)

    async def add_many(
        self, db: AsyncSession, user_id: str, site_id: str, ranks: dict[str, int | None]
    ) -> list[str]:
        if not ranks:
            return []
        now = datetime.now(UTC)
        statement = insert(SiteCompetitor).values(
            [
                {
                    "id": uid(COMPETITOR_ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "domain": domain,
                    "domain_rank": rank,
                    "created_at": now,
                    "updated_at": now,
                }
                for domain, rank in ranks.items()
            ]
        )
        added = await db.scalars(
            statement.on_conflict_do_nothing(index_elements=["site_id", "domain"]).returning(
                SiteCompetitor.domain
            )
        )
        return list(added)

    async def mark_fetched(self, db: AsyncSession, site_id: str, domain: str) -> None:
        now = datetime.now(UTC)
        await db.execute(
            update(SiteCompetitor)
            .where(SiteCompetitor.site_id == site_id, SiteCompetitor.domain == domain)
            .values(backlinks_fetched_at=now, updated_at=now)
        )

    async def delete_domains(self, db: AsyncSession, site_id: str, domains: list[str]) -> list[str]:
        if not domains:
            return []
        removed = await db.scalars(
            delete(SiteCompetitor)
            .where(SiteCompetitor.site_id == site_id, SiteCompetitor.domain.in_(domains))
            .returning(SiteCompetitor.domain)
        )
        return list(removed)


site_competitors = CompetitorRepository()
