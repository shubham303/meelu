from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.common.repository import now, page
from src.seo.keyword_gsc_pages.model import SeoKeywordGscPage
from src.seo.keyword_gsc_pages.schemas import KeywordGscPageRecord

SET_CTR_GAP_SQL = "update seo_keyword_gsc_pages set ctr_gap = :gap where id = :id"

SET_COVERAGE_SQL = """
update seo_keyword_gsc_pages set coverage = :coverage, lexical_hit = :lexical_hit,
  updated_at = now()
where id = :id
"""

UPSERT_COLUMNS = (
    "position",
    "impressions_28d",
    "clicks_28d",
    "impressions_prev_28d",
    "clicks_prev_28d",
    "impressions_ly_28d",
    "clicks_ly_28d",
    "ctr",
    "leader_days_90d",
    "computed_at",
)


class SeoKeywordGscPageRepository:
    ID_PREFIX = "kgp"
    UPSERT_CHUNK = 1000

    async def list_for_keyword(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> list[KeywordGscPageRecord]:
        rows = (
            await db.execute(
                select(SeoKeywordGscPage)
                .where(
                    SeoKeywordGscPage.site_id == site_id,
                    SeoKeywordGscPage.keyword_id == keyword_id,
                )
                .order_by(SeoKeywordGscPage.impressions_28d.desc())
            )
        ).scalars()
        return [KeywordGscPageRecord.model_validate(r) for r in rows]

    async def list_for_keywords(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> list[KeywordGscPageRecord]:
        if not keyword_ids:
            return []
        rows = (
            await db.execute(
                select(SeoKeywordGscPage).where(
                    SeoKeywordGscPage.site_id == site_id,
                    SeoKeywordGscPage.keyword_id.in_(set(keyword_ids)),
                )
            )
        ).scalars()
        return [KeywordGscPageRecord.model_validate(r) for r in rows]

    async def list_for_site(
        self,
        db: AsyncSession,
        site_id: str,
        page_ids: list[str] | None = None,
        keyword_ids: list[str] | None = None,
    ) -> list[KeywordGscPageRecord]:
        query = select(SeoKeywordGscPage).where(SeoKeywordGscPage.site_id == site_id)
        if page_ids is not None:
            query = query.where(SeoKeywordGscPage.page_id.in_(set(page_ids)))
        if keyword_ids is not None:
            query = query.where(SeoKeywordGscPage.keyword_id.in_(set(keyword_ids)))
        rows = (
            await db.execute(
                query.order_by(SeoKeywordGscPage.impressions_28d.desc(), SeoKeywordGscPage.seq)
            )
        ).scalars()
        return [KeywordGscPageRecord.model_validate(r) for r in rows]

    async def list_leaders(
        self, db: AsyncSession, site_id: str, min_days: int
    ) -> list[KeywordGscPageRecord]:
        rows = (
            await db.execute(
                select(SeoKeywordGscPage)
                .where(
                    SeoKeywordGscPage.site_id == site_id,
                    SeoKeywordGscPage.leader_days_90d >= min_days,
                )
                .order_by(SeoKeywordGscPage.seq)
            )
        ).scalars()
        return [KeywordGscPageRecord.model_validate(r) for r in rows]

    async def list_for_page(
        self, db: AsyncSession, site_id: str, page_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[KeywordGscPageRecord]:
        query = select(SeoKeywordGscPage).where(
            SeoKeywordGscPage.site_id == site_id, SeoKeywordGscPage.page_id == page_id
        )
        return await page(
            db, query, SeoKeywordGscPage.impressions_28d.desc(), paging, KeywordGscPageRecord
        )

    async def coverage_of(
        self, db: AsyncSession, site_id: str, keyword_id: str, page_id: str
    ) -> float | None:
        value = (
            await db.execute(
                select(SeoKeywordGscPage.coverage).where(
                    SeoKeywordGscPage.site_id == site_id,
                    SeoKeywordGscPage.keyword_id == keyword_id,
                    SeoKeywordGscPage.page_id == page_id,
                )
            )
        ).scalar_one_or_none()
        return None if value is None else float(value)

    async def ranking_keyword_ids(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str], max_position: float
    ) -> set[str]:
        if not keyword_ids:
            return set()
        rows = await db.execute(
            select(SeoKeywordGscPage.keyword_id).where(
                SeoKeywordGscPage.site_id == site_id,
                SeoKeywordGscPage.keyword_id.in_(set(keyword_ids)),
                SeoKeywordGscPage.position <= max_position,
            )
        )
        return set(rows.scalars().all())

    async def upsert_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        rows: list[dict[str, Any]],
        started: datetime,
    ) -> int:
        at = now()
        for start in range(0, len(rows), self.UPSERT_CHUNK):
            stmt = insert(SeoKeywordGscPage).values(
                [
                    {
                        "id": uid(self.ID_PREFIX),
                        "user_id": user_id,
                        "site_id": site_id,
                        "computed_at": started,
                        "created_at": at,
                        "updated_at": at,
                        **r,
                    }
                    for r in rows[start : start + self.UPSERT_CHUNK]
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["keyword_id", "page_id"],
                set_={
                    **{c: getattr(stmt.excluded, c) for c in UPSERT_COLUMNS},
                    "updated_at": at,
                },
            )
            await db.execute(stmt)
        return len(rows)

    async def prune_before(self, db: AsyncSession, site_id: str, started: datetime) -> None:
        await db.execute(
            delete(SeoKeywordGscPage).where(
                SeoKeywordGscPage.site_id == site_id, SeoKeywordGscPage.computed_at < started
            )
        )

    async def ctr_rows(
        self, db: AsyncSession, site_id: str, floor: int
    ) -> list[tuple[str, str, float, float, int]]:
        rows = await db.execute(
            select(
                SeoKeywordGscPage.id,
                SeoKeywordGscPage.keyword_id,
                SeoKeywordGscPage.position,
                SeoKeywordGscPage.ctr,
                SeoKeywordGscPage.impressions_28d,
            ).where(
                SeoKeywordGscPage.site_id == site_id,
                SeoKeywordGscPage.position.is_not(None),
                SeoKeywordGscPage.ctr.is_not(None),
                SeoKeywordGscPage.impressions_28d >= floor,
            )
        )
        return list(rows.tuples().all())

    async def ctr_gap_values(self, db: AsyncSession, site_id: str) -> list[tuple[str, float]]:
        rows = await db.execute(
            select(
                SeoKeywordGscPage.keyword_id,
                SeoKeywordGscPage.ctr_gap * SeoKeywordGscPage.impressions_28d,
            ).where(SeoKeywordGscPage.site_id == site_id, SeoKeywordGscPage.ctr_gap > 0)
        )
        return [(k, float(v)) for k, v in rows.tuples()]

    async def set_ctr_gaps(self, db: AsyncSession, gaps: list[dict[str, Any]]) -> None:
        if gaps:
            await db.execute(text(SET_CTR_GAP_SQL), gaps)

    async def set_coverage_many(self, db: AsyncSession, rows: list[dict[str, Any]]) -> None:
        if rows:
            await db.execute(text(SET_COVERAGE_SQL), rows)


seo_keyword_gsc_pages = SeoKeywordGscPageRepository()
