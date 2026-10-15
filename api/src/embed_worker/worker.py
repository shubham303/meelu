import asyncio
import signal
import sys

import src.core.tables  # noqa: F401
from src.core.database import engine
from src.site_pages.llm_extraction.classify import site_page_classifier

from .embedding import Embedder
from .service import embed_worker_service
from .settings import WorkerSettings

stopping = False


def request_stop(signum, frame):
    global stopping
    stopping = True


async def run_embed_passes(settings: WorkerSettings, embedder: Embedder) -> int:
    model = settings.meelu_embed_model
    pages, chunks = await embed_worker_service.run_chunk_pass(settings.meelu_chunk_page_batch)
    if pages > 0:
        print(f"embed-worker: re-chunked {pages} page(s) into {chunks} passage(s)")
    embedded = await embed_worker_service.run_embed_pass(embedder, model)
    if embedded > 0:
        print(f"embed-worker: embedded {embedded} chunk(s)")
    listening = await embed_worker_service.run_listening_pass(
        embedder,
        model,
        settings.meelu_listening_batch,
        settings.meelu_listening_max_batches,
    )
    if listening > 0:
        print(f"embed-worker: embedded {listening} listening row(s)")
    return pages + embedded + listening


async def run_extraction_passes() -> int:
    extracted = await site_page_classifier.run_extraction_pass()
    if extracted > 0:
        print(f"embed-worker: extracted {extracted} page(s)")
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
            print(f"embed-worker: {name} pass failed — {e}", file=sys.stderr)
            if once:
                return
            await asyncio.sleep(interval)


async def run(settings: WorkerSettings) -> None:
    print(f"embed-worker: loading {settings.meelu_embed_model}…")
    embedder = Embedder(settings.meelu_embed_model, settings.meelu_onnx_threads)
    interval = settings.meelu_embed_interval_ms / 1000
    print(
        f"embed-worker: ready — chunking and embedding every {settings.meelu_embed_interval_ms}ms"
    )
    once = settings.meelu_embed_once == "1"
    try:
        await asyncio.gather(
            loop("embed", lambda: run_embed_passes(settings, embedder), interval, once),
            loop("extraction", run_extraction_passes, interval, once),
        )
    finally:
        await engine.dispose()


def main():
    settings = WorkerSettings()

    if not settings.database_url:
        print("embed-worker: DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    if settings.meelu_embed_disabled == "1":
        print("embed-worker: disabled (MEELU_EMBED_DISABLED=1) — exiting rather than idle forever")
        sys.exit(0)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    asyncio.run(run(settings))
