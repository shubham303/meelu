from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.common.repository import now
from src.seo.keyword_content_pages.model import SeoKeywordContentPage
from src.seo.keyword_content_pages.schemas import KeywordContentPageRecord


class SeoKeywordContentPageRepository:
    ID_PREFIX = "kcp"
    UPSERT_CHUNK = 1000

    async def list_for_keyword(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> list[KeywordContentPageRecord]:
        rows = (
            await db.execute(
                select(SeoKeywordContentPage)
                .where(
                    SeoKeywordContentPage.site_id == site_id,
                    SeoKeywordContentPage.keyword_id == keyword_id,
                )
                .order_by(SeoKeywordContentPage.coverage.desc())
            )
        ).scalars()
        return [KeywordContentPageRecord.model_validate(r) for r in rows]

    async def list_for_keywords(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> list[KeywordContentPageRecord]:
        if not keyword_ids:
            return []
        rows = (
            await db.execute(
                select(SeoKeywordContentPage)
                .where(
                    SeoKeywordContentPage.site_id == site_id,
                    SeoKeywordContentPage.keyword_id.in_(set(keyword_ids)),
                )
                .order_by(SeoKeywordContentPage.coverage.desc())
            )
        ).scalars()
        return [KeywordContentPageRecord.model_validate(r) for r in rows]

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[KeywordContentPageRecord]:
        rows = (
            await db.execute(
                select(SeoKeywordContentPage)
                .where(SeoKeywordContentPage.site_id == site_id)
                .order_by(SeoKeywordContentPage.coverage.desc())
            )
        ).scalars()
        return [KeywordContentPageRecord.model_validate(r) for r in rows]

    async def coverage_of(
        self, db: AsyncSession, site_id: str, keyword_id: str, page_id: str
    ) -> float | None:
        value = (
            await db.execute(
                select(SeoKeywordContentPage.coverage).where(
                    SeoKeywordContentPage.site_id == site_id,
                    SeoKeywordContentPage.keyword_id == keyword_id,
                    SeoKeywordContentPage.page_id == page_id,
                )
            )
        ).scalar_one_or_none()
        return None if value is None else float(value)

    async def upsert_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        rows: list[dict[str, Any]],
        started: datetime,
    ) -> None:
        at = now()
        for start in range(0, len(rows), self.UPSERT_CHUNK):
            stmt = insert(SeoKeywordContentPage).values(
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
                    "coverage": stmt.excluded.coverage,
                    "lexical_hit": stmt.excluded.lexical_hit,
                    "computed_at": stmt.excluded.computed_at,
                    "updated_at": at,
                },
            )
            await db.execute(stmt)

    async def prune_before(
        self, db: AsyncSession, keyword_ids: list[str], started: datetime
    ) -> None:
        if not keyword_ids:
            return
        await db.execute(
            delete(SeoKeywordContentPage).where(
                SeoKeywordContentPage.keyword_id.in_(set(keyword_ids)),
                SeoKeywordContentPage.computed_at < started,
            )
        )


seo_keyword_content_pages = SeoKeywordContentPageRepository()
