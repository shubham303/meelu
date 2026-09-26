from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.competitor_keywords.model import SeoCompetitorKeyword
from src.seo.competitor_keywords.schemas import CompetitorKeywordRecord

UPSERT_SQL = """
insert into seo_competitor_keywords (id, user_id, site_id, competitor_id, keyword_id, position,
  url, etv, fetched_at, created_at, updated_at)
values (:id, :user_id, :site_id, :competitor_id, :keyword_id, :position, :url, :etv, :at, :at, :at)
on conflict (competitor_id, keyword_id) do update set position = excluded.position,
  url = excluded.url, etv = excluded.etv, fetched_at = excluded.fetched_at, updated_at = excluded.updated_at
"""


class SeoCompetitorKeywordRepository:
    ID_PREFIX = "ckw"

    async def latest_fetched_at(self, db: AsyncSession, competitor_id: str) -> datetime | None:
        return (
            await db.execute(
                select(func.max(SeoCompetitorKeyword.fetched_at)).where(
                    SeoCompetitorKeyword.competitor_id == competitor_id
                )
            )
        ).scalar()

    async def upsert_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        competitor_id: str,
        rows: list[dict[str, Any]],
        at: datetime,
    ) -> None:
        if not rows:
            return
        await db.execute(
            text(UPSERT_SQL),
            [
                {
                    "id": uid(self.ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "competitor_id": competitor_id,
                    "keyword_id": r["keyword_id"],
                    "position": r.get("position"),
                    "url": r.get("url"),
                    "etv": r.get("etv"),
                    "at": at,
                }
                for r in rows
            ],
        )

    async def list_by_keyword_ids(
        self,
        db: AsyncSession,
        site_id: str,
        keyword_ids: list[str],
        max_position: int | None = None,
    ) -> list[CompetitorKeywordRecord]:
        if not keyword_ids:
            return []
        query = select(SeoCompetitorKeyword).where(
            SeoCompetitorKeyword.site_id == site_id,
            SeoCompetitorKeyword.keyword_id.in_(set(keyword_ids)),
        )
        if max_position is not None:
            query = query.where(SeoCompetitorKeyword.position <= max_position)
        rows = (await db.execute(query.order_by(SeoCompetitorKeyword.seq))).scalars()
        return [CompetitorKeywordRecord.model_validate(r) for r in rows]

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[CompetitorKeywordRecord]:
        rows = (
            await db.execute(
                select(SeoCompetitorKeyword)
                .where(SeoCompetitorKeyword.site_id == site_id)
                .order_by(SeoCompetitorKeyword.position.nulls_last(), SeoCompetitorKeyword.seq)
            )
        ).scalars()
        return [CompetitorKeywordRecord.model_validate(r) for r in rows]


seo_competitor_keywords = SeoCompetitorKeywordRepository()
