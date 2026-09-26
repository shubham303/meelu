from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.models.page_facts import SeoPageFacts
from src.seo.repositories.base import now, page
from src.seo.schemas import PageFactsRecord

UPSERT_COLUMNS = (
    "url",
    "status",
    "redirect_to",
    "page_type",
    "lang",
    "title",
    "h1",
    "headings",
    "meta_description",
    "title_pixels",
    "word_count",
    "inlinks",
    "link_score",
    "published_at",
    "content_hash",
    "indexable",
    "live",
    "is_home",
    "impressions_28d",
    "clicks_28d",
    "impressions_ly_28d",
    "clicks_ly_28d",
)


class SeoPageFactsRepository:
    ID_PREFIX = "pf"
    UPSERT_CHUNK = 500

    async def get(self, db: AsyncSession, site_id: str, page_id: str) -> PageFactsRecord | None:
        row = (
            await db.execute(
                select(SeoPageFacts).where(
                    SeoPageFacts.site_id == site_id, SeoPageFacts.page_id == page_id
                )
            )
        ).scalar_one_or_none()
        return None if row is None else PageFactsRecord.model_validate(row)

    async def list_by_page_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> list[PageFactsRecord]:
        if not page_ids:
            return []
        rows = (
            await db.execute(
                select(SeoPageFacts).where(
                    SeoPageFacts.site_id == site_id, SeoPageFacts.page_id.in_(set(page_ids))
                )
            )
        ).scalars()
        return [PageFactsRecord.model_validate(r) for r in rows]

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[PageFactsRecord]:
        rows = (
            await db.execute(
                select(SeoPageFacts).where(SeoPageFacts.site_id == site_id).order_by(SeoPageFacts.seq)
            )
        ).scalars()
        return [PageFactsRecord.model_validate(r) for r in rows]

    async def live_page_ids(
        self, db: AsyncSession, site_id: str, page_types: list[str] | None = None
    ) -> list[str]:
        query = select(SeoPageFacts.page_id).where(
            SeoPageFacts.site_id == site_id, SeoPageFacts.live
        )
        if page_types is not None:
            query = query.where(SeoPageFacts.page_type.in_(page_types))
        return list((await db.execute(query)).scalars().all())

    async def inlinks_median(self, db: AsyncSession, site_id: str) -> float:
        value = (
            await db.execute(
                select(func.percentile_cont(0.5).within_group(SeoPageFacts.inlinks)).where(
                    SeoPageFacts.site_id == site_id, SeoPageFacts.live
                )
            )
        ).scalar()
        return float(value or 0)

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[dict[str, Any]]
    ) -> int:
        at = now()
        for start in range(0, len(rows), self.UPSERT_CHUNK):
            chunk = rows[start : start + self.UPSERT_CHUNK]
            stmt = insert(SeoPageFacts).values(
                [
                    {
                        "id": uid(self.ID_PREFIX),
                        "user_id": user_id,
                        "site_id": site_id,
                        "created_at": at,
                        "updated_at": at,
                        **r,
                    }
                    for r in chunk
                ]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["page_id"],
                set_={
                    **{c: getattr(stmt.excluded, c) for c in UPSERT_COLUMNS},
                    "first_seen_at": func.coalesce(
                        SeoPageFacts.first_seen_at, stmt.excluded.first_seen_at
                    ),
                    "updated_at": at,
                },
            )
            await db.execute(stmt)
        return len(rows)

    async def retire_except(self, db: AsyncSession, site_id: str, keep_page_ids: list[str]) -> int:
        result = await db.execute(
            update(SeoPageFacts)
            .where(
                SeoPageFacts.site_id == site_id,
                SeoPageFacts.live,
                SeoPageFacts.page_id.not_in(keep_page_ids),
            )
            .values(live=False, indexable=False, updated_at=now())
        )
        return result.rowcount or 0

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams, live: bool | None
    ) -> PaginatedApiResponse[PageFactsRecord]:
        query = select(SeoPageFacts).where(SeoPageFacts.site_id == site_id)
        if live is not None:
            query = query.where(SeoPageFacts.live == live)
        return await page(db, query, SeoPageFacts.url, paging, PageFactsRecord)


seo_page_facts = SeoPageFactsRepository()
