from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_pages.llm_extraction import repository as repo
from src.site_pages.schemas.llm_extraction import (
    PageLlmExtractionCreateRequest,
    PageLlmExtractionRecord,
    PageLlmExtractionStatsRecord,
)


async def stats(db: AsyncSession, site_id: str) -> PageLlmExtractionStatsRecord:
    eligible, extracted, pending = await repo.counts(db, site_id)
    return PageLlmExtractionStatsRecord(eligible=eligible, extracted=extracted, pending=pending)


async def save(
    db: AsyncSession, user_id: str, site_id: str, body: PageLlmExtractionCreateRequest
) -> PageLlmExtractionRecord:
    if not await repo.page_exists(db, site_id, body.page_id):
        raise HTTPException(404, f"No page {body.page_id} for this website.")
    return await repo.upsert(db, user_id, site_id, body)


async def set_page_type(
    db: AsyncSession, user_id: str, site_id: str, page_id: str, page_type: str
) -> PageLlmExtractionRecord:
    if not await repo.page_exists(db, site_id, page_id):
        raise HTTPException(404, f"No page {page_id} for this website.")
    saved = await repo.set_page_type(db, user_id, site_id, page_id, page_type)
    if saved is None:
        raise HTTPException(409, f"Page {page_id} already has a page type.")
    return saved


async def get(db: AsyncSession, site_id: str, extraction_id: str) -> PageLlmExtractionRecord:
    found = await repo.by_id(db, site_id, extraction_id)
    if found is None:
        raise HTTPException(404, f"No page extraction {extraction_id} for this website.")
    return found


async def get_by_page(db: AsyncSession, site_id: str, page_id: str) -> PageLlmExtractionRecord:
    found = await repo.by_page(db, site_id, page_id)
    if found is None:
        raise HTTPException(404, f"Page {page_id} has not been extracted yet.")
    return found


async def list_extractions(
    db: AsyncSession, site_id: str, page_type: str | None, paging: PaginationParams
) -> PaginatedApiResponse[PageLlmExtractionRecord]:
    return await repo.list_extractions(db, site_id, page_type, paging)


async def delete(db: AsyncSession, site_id: str, extraction_id: str) -> None:
    if not await repo.remove(db, site_id, extraction_id):
        raise HTTPException(404, f"No page extraction {extraction_id} for this website.")
