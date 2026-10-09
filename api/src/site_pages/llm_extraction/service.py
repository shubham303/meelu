from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_pages.llm_extraction.questions import (
    MAX_BODY_CHARS,
    QUESTIONS,
    invalid_review_answers,
    read_review_answers,
)
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas.llm_extraction import (
    ExtractionState,
    PageLlmExtractionCreateRequest,
    PageLlmExtractionRecord,
    PageLlmExtractionReviewRequest,
    PageLlmExtractionStatsRecord,
    PendingPageRecord,
    ReviewPageRecord,
    ReviewQueueRecord,
)
from src.sites.repository import sites

MAX_EXTRACT_ATTEMPTS = 3


class SitePageLlmExtractionService:
    async def stats(self, db: AsyncSession, site_id: str) -> PageLlmExtractionStatsRecord:
        hashes = await site_pages.extractable_hashes(db, site_id)
        states = await site_page_llm_extractions.states_by_page_ids(
            db, site_id, [page_id for page_id, _ in hashes]
        )
        extracted = sum(1 for page_id, h in hashes if self._is_extracted(states.get(page_id), h))
        pending = sum(1 for page_id, h in hashes if self._is_pending(states.get(page_id), h))
        return PageLlmExtractionStatsRecord(
            eligible=len(hashes), extracted=extracted, pending=pending
        )

    async def pending_pages(
        self, db: AsyncSession, site_id: str, limit: int
    ) -> tuple[list[PendingPageRecord], int]:
        hashes = await site_pages.extractable_hashes(db, site_id)
        states = await site_page_llm_extractions.states_by_page_ids(
            db, site_id, [page_id for page_id, _ in hashes]
        )
        pending = [page_id for page_id, h in hashes if self._is_pending(states.get(page_id), h)]
        return (
            await site_pages.pending_records_by_ids(db, site_id, pending[:limit]),
            len(pending),
        )

    async def pending_sites(
        self, db: AsyncSession, site_id: str | None = None
    ) -> list[tuple[str, str]]:
        refs = await sites.list_refs(
            db, ids=[site_id] if site_id is not None else None, status="active"
        )
        site_ids = [r.id for r in refs]
        hashes_by_site = await site_pages.extractable_hashes_by_site_ids(db, site_ids)
        states = await site_page_llm_extractions.states_by_site_ids(db, list(hashes_by_site))
        return [
            (r.user_id, r.id)
            for r in refs
            if any(
                self._is_pending(states.get(page_id), h)
                for page_id, h in hashes_by_site.get(r.id, {}).items()
            )
        ]

    async def save(
        self, db: AsyncSession, user_id: str, site_id: str, body: PageLlmExtractionCreateRequest
    ) -> PageLlmExtractionRecord:
        if not await site_pages.exists(db, site_id, body.page_id):
            raise HTTPException(404, f"No page {body.page_id} for this website.")
        return await site_page_llm_extractions.upsert(db, user_id, site_id, body)

    async def set_page_type(
        self, db: AsyncSession, user_id: str, site_id: str, page_id: str, page_type: str
    ) -> PageLlmExtractionRecord:
        hashes = await site_pages.content_hashes_by_ids(db, site_id, [page_id])
        if page_id not in hashes:
            raise HTTPException(404, f"No page {page_id} for this website.")
        saved = await site_page_llm_extractions.set_page_type(
            db, user_id, site_id, page_id, page_type, hashes[page_id]
        )
        if saved is None:
            raise HTTPException(409, f"Page {page_id} already has a page type.")
        return saved

    async def review_queue(self, db: AsyncSession, site_id: str, limit: int) -> ReviewQueueRecord:
        queued = await site_page_llm_extractions.review_queue(db, site_id)
        hashes = await site_pages.content_hashes_by_ids(db, site_id, [p for p, _ in queued])
        current = [p for p, h in queued if h is not None and hashes.get(p) == h]
        pages = await site_pages.pending_records_by_ids(db, site_id, current[:limit])
        return ReviewQueueRecord(
            questions=QUESTIONS,
            pages=[
                ReviewPageRecord(
                    page_id=p.id,
                    url=p.url,
                    title=p.title,
                    h1=p.h1,
                    meta_description=p.meta_description,
                    content_hash=p.content_hash or "",
                    body_text=(p.body_text or "")[:MAX_BODY_CHARS],
                )
                for p in pages
            ],
            total=len(current),
        )

    async def save_review(
        self, db: AsyncSession, site_id: str, page_id: str, body: PageLlmExtractionReviewRequest
    ) -> PageLlmExtractionRecord:
        invalid = invalid_review_answers(body.answers)
        if invalid:
            raise HTTPException(422, f"Missing or unknown answer for {', '.join(invalid)}.")
        hashes = await site_pages.content_hashes_by_ids(db, site_id, [page_id])
        if page_id not in hashes:
            raise HTTPException(404, f"No page {page_id} for this website.")
        if hashes[page_id] != body.content_hash:
            raise HTTPException(409, f"Page {page_id} changed since it was queued for review.")
        saved = await site_page_llm_extractions.save_review(
            db, site_id, page_id, body.content_hash, body.model, read_review_answers(body.answers)
        )
        if saved is None:
            raise HTTPException(409, f"Page {page_id} is not waiting for a review.")
        return saved

    async def get(
        self, db: AsyncSession, site_id: str, extraction_id: str
    ) -> PageLlmExtractionRecord:
        found = await site_page_llm_extractions.get(db, site_id, extraction_id)
        if found is None:
            raise HTTPException(404, f"No page extraction {extraction_id} for this website.")
        return found

    async def get_by_page(
        self, db: AsyncSession, site_id: str, page_id: str
    ) -> PageLlmExtractionRecord:
        found = await site_page_llm_extractions.get_by_page(db, site_id, page_id)
        if found is None:
            raise HTTPException(404, f"Page {page_id} has not been extracted yet.")
        return found

    async def list_extractions(
        self, db: AsyncSession, site_id: str, page_type: str | None, paging: PaginationParams
    ) -> PaginatedApiResponse[PageLlmExtractionRecord]:
        return await site_page_llm_extractions.list_filtered(db, site_id, page_type, paging)

    async def delete(self, db: AsyncSession, site_id: str, extraction_id: str) -> None:
        if not await site_page_llm_extractions.delete(db, site_id, extraction_id):
            raise HTTPException(404, f"No page extraction {extraction_id} for this website.")

    def _is_pending(self, state: ExtractionState | None, content_hash: str) -> bool:
        if state is None or state.extracted_from_hash != content_hash:
            return True
        return state.error is not None and state.extract_attempts < MAX_EXTRACT_ATTEMPTS

    def _is_extracted(self, state: ExtractionState | None, content_hash: str) -> bool:
        return (
            state is not None and state.error is None and state.extracted_from_hash == content_hash
        )


site_page_llm_extraction_service = SitePageLlmExtractionService()
