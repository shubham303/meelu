from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.schemas.llm_extraction import (
    PageLlmExtractionCreateRequest,
    PageLlmExtractionRecord,
    PendingPageRecord,
)
from src.site_pages.models.site_page import SitePage
from src.sites.models.site import Site

MAX_EXTRACT_ATTEMPTS = 3


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
        and_(
            SitePageLlmExtraction.error.is_not(None),
            SitePageLlmExtraction.extract_attempts < MAX_EXTRACT_ATTEMPTS,
        ),
    )


def _pages_with_extraction(site_id: str):
    return (
        select(SitePage)
        .join(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id, isouter=True)
        .where(*_eligible(site_id))
    )


async def set_page_type(
    db: AsyncSession, user_id: str, site_id: str, page_id: str, page_type: str
) -> PageLlmExtractionRecord | None:
    content_hash = (
        await db.execute(
            select(SitePage.content_hash).where(SitePage.site_id == site_id, SitePage.id == page_id)
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    stmt = (
        pg_insert(SitePageLlmExtraction)
        .values(
            id=uid("spx"),
            user_id=user_id,
            site_id=site_id,
            page_id=page_id,
            page_type=page_type,
            extracted_from_hash=content_hash,
            created_at=now,
            extracted_at=now,
            updated_at=now,
            extract_attempts=0,
        )
        .on_conflict_do_update(
            index_elements=[SitePageLlmExtraction.page_id],
            set_={
                "page_type": page_type,
                "extracted_from_hash": content_hash,
                "error": None,
                "extract_attempts": 0,
                "updated_at": now,
            },
            where=SitePageLlmExtraction.page_type.is_(None),
        )
        .returning(SitePageLlmExtraction.id)
    )
    saved = (await db.execute(stmt)).scalar_one_or_none()
    if saved is None:
        return None
    await db.flush()
    return await by_id(db, site_id, saved)


async def page_exists(db: AsyncSession, site_id: str, page_id: str) -> bool:
    result = await db.execute(
        select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id == page_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def pending_pages(
    db: AsyncSession, site_id: str, limit: int
) -> tuple[list[PendingPageRecord], int]:
    base = _pages_with_extraction(site_id).where(_pending())
    total = (
        await db.execute(select(func.count()).select_from(base.order_by(None).subquery()))
    ).scalar_one()
    rows = (await db.execute(base.order_by(SitePage.seq.asc()).limit(limit))).scalars().all()
    return [PendingPageRecord.model_validate(r) for r in rows], total


async def pending_sites(db: AsyncSession, site_id: str | None = None) -> list[tuple[str, str]]:
    has_pending = exists(
        select(SitePage.id)
        .join(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id, isouter=True)
        .where(*_eligible(Site.id), _pending())
    )
    stmt = select(Site.user_id, Site.id).where(Site.status == "active", has_pending)
    if site_id is not None:
        stmt = stmt.where(Site.id == site_id)
    rows = await db.execute(stmt)
    return [(user_id, sid) for user_id, sid in rows.tuples().all()]


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
    pending_q = _pages_with_extraction(site_id).where(_pending())
    pending = (
        await db.execute(select(func.count()).select_from(pending_q.order_by(None).subquery()))
    ).scalar_one()
    return eligible, extracted, pending


async def upsert(
    db: AsyncSession, user_id: str, site_id: str, body: PageLlmExtractionCreateRequest
) -> PageLlmExtractionRecord:
    now = datetime.now(UTC)
    values: dict[str, Any] = {**body.values(), "extracted_at": now, "updated_at": now}
    failed = body.error is not None
    stmt = (
        pg_insert(SitePageLlmExtraction)
        .values(
            id=uid("spx"),
            user_id=user_id,
            site_id=site_id,
            page_id=body.page_id,
            created_at=now,
            extract_attempts=1 if failed else 0,
            **values,
        )
        .on_conflict_do_update(
            index_elements=[SitePageLlmExtraction.page_id],
            set_={
                **values,
                "extract_attempts": (SitePageLlmExtraction.extract_attempts + 1 if failed else 0),
            },
        )
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
