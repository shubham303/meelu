from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_page_llm_extraction.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_page_llm_extraction.schemas import (
    PageLlmExtractionCreateRequest,
    PageLlmExtractionRecord,
    PendingPageRecord,
)
from src.site_pages.models.site_page import SitePage


def _fresh(stmt):
    return stmt.execution_options(populate_existing=True)


def _eligible(site_id: str):
    return (
        SitePage.site_id == site_id,
        SitePage.body_text.is_not(None),
        SitePage.body_text != "",
        SitePage.content_hash.is_not(None),
    )


def _pending():
    return or_(
        SitePageLlmExtraction.id.is_(None),
        SitePageLlmExtraction.extracted_from_hash.is_distinct_from(SitePage.content_hash),
        SitePageLlmExtraction.error.is_not(None),
    )


def _pages_with_extraction(site_id: str):
    return (
        select(SitePage)
        .join(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id, isouter=True)
        .where(*_eligible(site_id))
    )


async def page_exists(db: AsyncSession, site_id: str, page_id: str) -> bool:
    result = await db.execute(
        select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id == page_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def pending_pages(
    db: AsyncSession, site_id: str, limit: int, exclude_ids: list[str] | None = None
) -> tuple[list[PendingPageRecord], int]:
    base = _pages_with_extraction(site_id).where(_pending())
    if exclude_ids:
        base = base.where(SitePage.id.not_in(exclude_ids))
    total = (
        await db.execute(select(func.count()).select_from(base.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(base.order_by(SitePage.seq.asc()).limit(limit))).scalars().all()
    return [PendingPageRecord.model_validate(r) for r in rows], total


async def counts(db: AsyncSession, site_id: str) -> tuple[int, int, int]:
    eligible = (
        await db.execute(select(func.count()).select_from(SitePage).where(*_eligible(site_id)))
    ).scalar_one()
    extracted_q = _pages_with_extraction(site_id).where(
        SitePageLlmExtraction.id.is_not(None),
        SitePageLlmExtraction.error.is_(None),
        SitePageLlmExtraction.extracted_from_hash == SitePage.content_hash,
    )
    extracted = (
        await db.execute(select(func.count()).select_from(extracted_q.order_by(None).subquery()))
    ).scalar_one()
    return eligible, extracted, eligible - extracted


async def upsert(
    db: AsyncSession, user_id: str, site_id: str, body: PageLlmExtractionCreateRequest
) -> PageLlmExtractionRecord:
    now = datetime.now(UTC)
    values: dict[str, Any] = {**body.values(), "extracted_at": now, "updated_at": now}
    stmt = (
        pg_insert(SitePageLlmExtraction)
        .values(
            id=uid("spx"),
            user_id=user_id,
            site_id=site_id,
            page_id=body.page_id,
            created_at=now,
            **values,
        )
        .on_conflict_do_update(index_elements=[SitePageLlmExtraction.page_id], set_=values)
        .returning(SitePageLlmExtraction.id)
    )
    saved = (await db.execute(stmt)).scalar_one()
    await db.flush()
    return await by_id(db, site_id, saved)


async def by_id(
    db: AsyncSession, site_id: str, extraction_id: str
) -> PageLlmExtractionRecord | None:
    result = await db.execute(
        _fresh(
            select(SitePageLlmExtraction)
            .where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.id == extraction_id,
            )
            .limit(1)
        )
    )
    row = result.scalar_one_or_none()
    return None if row is None else PageLlmExtractionRecord.model_validate(row)


async def by_page(db: AsyncSession, site_id: str, page_id: str) -> PageLlmExtractionRecord | None:
    result = await db.execute(
        select(SitePageLlmExtraction)
        .where(SitePageLlmExtraction.site_id == site_id, SitePageLlmExtraction.page_id == page_id)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return None if row is None else PageLlmExtractionRecord.model_validate(row)


async def list_extractions(
    db: AsyncSession, site_id: str, page_type: str | None, paging: PaginationParams
) -> PaginatedApiResponse[PageLlmExtractionRecord]:
    stmt = select(SitePageLlmExtraction).where(SitePageLlmExtraction.site_id == site_id)
    if page_type:
        stmt = stmt.where(SitePageLlmExtraction.page_type == page_type)
    stmt = stmt.order_by(SitePageLlmExtraction.seq.desc())
    return await PaginationService.paginate_query(
        db,
        stmt,
        page=paging.page,
        page_size=paging.page_size,
        response_model=PageLlmExtractionRecord,
    )


async def remove(db: AsyncSession, site_id: str, extraction_id: str) -> bool:
    result = await db.execute(
        delete(SitePageLlmExtraction)
        .where(SitePageLlmExtraction.site_id == site_id, SitePageLlmExtraction.id == extraction_id)
        .returning(SitePageLlmExtraction.id)
    )
    return result.scalar_one_or_none() is not None
