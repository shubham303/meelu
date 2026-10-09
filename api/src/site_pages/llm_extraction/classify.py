import asyncio

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_pages.llm_extraction.questions import QUESTIONS, page_state, read_answers
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.llm_extraction.service import site_page_llm_extraction_service
from src.site_pages.schemas.llm_extraction import PageLlmExtractionCreateRequest, PendingPageRecord

BATCH = 50
CONCURRENCY = 8

log = get_logger("site_page_llm_extraction")


class SitePageClassifier:
    async def classify_page(self, user_id: str, site_id: str, page: PendingPageRecord) -> bool:
        caller = Caller(user_id=user_id, site_id=site_id)
        subject = {"page_id": page.id, "content_hash": page.content_hash}
        state = page_state(page.url, page.title, page.h1, page.meta_description, page.body_text)
        async with unit_of_work() as db:
            try:
                result = await json_data_extractor.decide(db, caller, subject, state, QUESTIONS)
            except ProviderRequestError as exc:
                await site_page_llm_extractions.upsert(
                    db,
                    user_id,
                    site_id,
                    PageLlmExtractionCreateRequest(
                        page_id=page.id, extracted_from_hash=page.content_hash, error=str(exc)
                    ),
                )
                return False
            await site_page_llm_extractions.upsert(
                db,
                user_id,
                site_id,
                PageLlmExtractionCreateRequest(
                    page_id=page.id,
                    extracted_from_hash=page.content_hash,
                    model=result.get("model"),
                    **read_answers(result["answers"]),
                ),
            )
            return True

    async def classify_site_batch(self, user_id: str, site_id: str) -> int:
        async with unit_of_work() as db:
            pages, _ = await site_page_llm_extraction_service.pending_pages(db, site_id, BATCH)
        if not pages:
            return 0
        gate = asyncio.Semaphore(CONCURRENCY)
        done = {"extracted": 0, "failed": 0}

        async def one(page: PendingPageRecord) -> None:
            async with gate:
                if await self.classify_page(user_id, site_id, page):
                    done["extracted"] += 1
                else:
                    done["failed"] += 1

        await asyncio.gather(*(one(p) for p in pages))
        log.info("page extraction batch", site_id=site_id, **done)
        return done["extracted"] + done["failed"]

    async def run_extraction_pass(self, site_id: str | None = None) -> int:
        async with unit_of_work() as db:
            pending = await site_page_llm_extraction_service.pending_sites(db, site_id)
        processed = 0
        for user_id, pending_site_id in pending:
            try:
                processed += await self.classify_site_batch(user_id, pending_site_id)
            except (NoProviderError, InsufficientCreditsError) as exc:
                log.warning("page extraction skipped", site_id=pending_site_id, reason=str(exc))
            except Exception:
                log.exception("page extraction crashed", site_id=pending_site_id)
        return processed


site_page_classifier = SitePageClassifier()
