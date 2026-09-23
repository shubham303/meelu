import asyncio

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_page_llm_extraction import repository as repo
from src.site_page_llm_extraction.questions import QUESTIONS, page_state, read_answers
from src.site_page_llm_extraction.schemas import PageLlmExtractionCreateRequest, PendingPageRecord
from src.sites import repository as sites_repo

BATCH = 50
CONCURRENCY = 8

log = get_logger("site_page_llm_extraction")

_running: dict[str, asyncio.Task] = {}


def running(site_id: str) -> bool:
    return site_id in _running and not _running[site_id].done()


def start(user_id: str, site_id: str) -> bool:
    if running(site_id):
        return False
    task = asyncio.create_task(classify_site(user_id, site_id))
    _running[site_id] = task
    task.add_done_callback(lambda _: _running.pop(site_id, None))
    return True


async def classify_page(user_id: str, site_id: str, page: PendingPageRecord) -> bool:
    caller = Caller(user_id=user_id, site_id=site_id)
    subject = {"page_id": page.id, "content_hash": page.content_hash}
    state = page_state(page.url, page.title, page.meta_description, page.body_text)
    async with unit_of_work() as db:
        try:
            result = await json_data_extractor.decide(db, caller, subject, state, QUESTIONS)
        except ProviderRequestError as exc:
            await repo.upsert(
                db,
                user_id,
                site_id,
                PageLlmExtractionCreateRequest(
                    page_id=page.id, extracted_from_hash=page.content_hash, error=str(exc)
                ),
            )
            return False
        await repo.upsert(
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


async def classify_site(user_id: str, site_id: str) -> dict[str, int]:
    done = {"extracted": 0, "failed": 0}
    failed_ids: list[str] = []
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(page: PendingPageRecord) -> None:
        async with gate:
            ok = await classify_page(user_id, site_id, page)
        if ok:
            done["extracted"] += 1
        else:
            done["failed"] += 1
            failed_ids.append(page.id)

    try:
        while True:
            async with unit_of_work() as db:
                site = await sites_repo.get_site(db, user_id, site_id)
                if site is None or site.status != "active":
                    log.info("page classification paused", site_id=site_id)
                    break
                pages, _ = await repo.pending_pages(db, site_id, BATCH, exclude_ids=failed_ids)
            if not pages:
                break
            await asyncio.gather(*(one(p) for p in pages))
    except (NoProviderError, InsufficientCreditsError) as exc:
        log.warning("page classification stopped", site_id=site_id, reason=str(exc))
    except Exception:
        log.exception("page classification crashed", site_id=site_id)
    log.info("page classification finished", site_id=site_id, **done)
    return done
