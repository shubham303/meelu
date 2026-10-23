import asyncio
import signal
import sys

import sentry_sdk

import src.core.tables  # noqa: F401
from src.core.database import engine
from src.core.logging import configure_error_reporting, configure_logging, get_logger
from src.site_pages.llm_extraction.classify import site_page_classifier

from .embedding import Embedder
from .service import embed_worker_service
from .settings import WorkerSettings

log = get_logger()

stopping = False


def request_stop(signum, frame):
    global stopping
    stopping = True


async def run_embed_passes(settings: WorkerSettings, embedder: Embedder) -> int:
    model = settings.meelu_embed_model
    pages, chunks = await embed_worker_service.run_chunk_pass(settings.meelu_chunk_page_batch)
    if pages > 0:
        log.info("embed_worker.chunk.pages_rechunked", pages=pages, chunks=chunks)
    embedded = await embed_worker_service.run_embed_pass(embedder, model)
    if embedded > 0:
        log.info("embed_worker.embed.chunks_embedded", chunks=embedded)
    listening = await embed_worker_service.run_listening_pass(
        embedder,
        model,
        settings.meelu_listening_batch,
        settings.meelu_listening_max_batches,
    )
    if listening > 0:
        log.info("embed_worker.embed.posts_embedded", posts=listening)
    return pages + embedded + listening


async def run_extraction_passes() -> int:
    extracted = await site_page_classifier.run_extraction_pass()
    if extracted > 0:
        log.info("embed_worker.extraction.pages_extracted", pages=extracted)
    return extracted


async def loop(name: str, passes, interval: float, once: bool) -> None:
    while not stopping:
        try:
            worked = await passes()
            if once:
                return
            if worked == 0:
                await asyncio.sleep(interval)
        except Exception as e:
            log.error("embed_worker.loop.pass_failed", loop=name, error=str(e))
            sentry_sdk.capture_exception(e)
            if once:
                return
            await asyncio.sleep(interval)


async def run(settings: WorkerSettings) -> None:
    log.info("embed_worker.model.loading", model=settings.meelu_embed_model)
    embedder = Embedder(settings.meelu_embed_model, settings.meelu_onnx_threads)
    interval = settings.meelu_embed_interval_ms / 1000
    log.info("embed_worker.loop.ready", interval_ms=settings.meelu_embed_interval_ms)
    once = settings.meelu_embed_once == "1"
    try:
        await asyncio.gather(
            loop("embed", lambda: run_embed_passes(settings, embedder), interval, once),
            loop("extraction", run_extraction_passes, interval, once),
        )
    finally:
        await engine.dispose()


def main():
    configure_logging()
    configure_error_reporting()
    settings = WorkerSettings()

    if not settings.database_url:
        log.error("embed_worker.startup.database_url_missing")
        sys.exit(1)

    if settings.meelu_embed_disabled == "1":
        log.info("embed_worker.startup.disabled")
        sys.exit(0)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    asyncio.run(run(settings))
