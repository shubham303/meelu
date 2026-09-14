import asyncio
import os
import threading

from src.core.logging import get_logger

log = get_logger("site_pages.embedding")

EMBED_MODEL = os.environ.get("MEELU_EMBED_MODEL", "Xenova/multilingual-e5-small")

_load_lock = threading.Lock()
_embed_lock = threading.Lock()
_state: list = [False, None]


def embeddings_enabled() -> bool:
    return os.environ.get("MEELU_EMBED_DISABLED") != "1"


def _embedder():
    if _state[0]:
        return _state[1]
    with _load_lock:
        if _state[0]:
            return _state[1]
        embedder = None
        if embeddings_enabled():
            try:
                from src.embed_worker.embedding import Embedder

                embedder = Embedder(EMBED_MODEL)
            except Exception as e:
                log.error("embedder_unavailable", model=EMBED_MODEL, error=str(e))
        _state[1] = embedder
        _state[0] = True
    return _state[1]


async def embed_query(q: str) -> list[float] | None:
    embedder = await asyncio.to_thread(_embedder)
    if embedder is None:
        return None

    def run() -> list[list[float]]:
        with _embed_lock:
            return embedder.embed([f"query: {q}"])

    vectors = await asyncio.to_thread(run)
    return vectors[0]
