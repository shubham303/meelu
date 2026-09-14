import asyncio
import os

from src.core.logging import get_logger

log = get_logger("notes.embedder")

EMBED_MODEL = os.environ.get("MEELU_EMBED_MODEL") or "Xenova/multilingual-e5-small"

_lock = asyncio.Lock()
_loaded = False
_embedder = None


def embeddings_enabled() -> bool:
    return os.environ.get("MEELU_EMBED_DISABLED") != "1"


def _load():
    global _loaded, _embedder
    if not embeddings_enabled():
        return None
    if _loaded:
        return _embedder
    _loaded = True
    try:
        from src.embed_worker.embedding import Embedder

        _embedder = Embedder(EMBED_MODEL)
    except Exception as e:
        log.error("embedder_unavailable", model=EMBED_MODEL, error=str(e))
        _embedder = None
    return _embedder


async def embed_texts(inputs: list[str]) -> list[list[float]] | None:
    async with _lock:
        embedder = await asyncio.to_thread(_load)
        if embedder is None:
            return None
        try:
            return await asyncio.to_thread(embedder.embed, inputs)
        except Exception as e:
            log.error("embed_failed", model=EMBED_MODEL, error=str(e))
            return None


async def embed_query(q: str) -> list[float] | None:
    vectors = await embed_texts([f"query: {q}"])
    return vectors[0] if vectors else None


async def embed_passage(text: str) -> list[float] | None:
    vectors = await embed_texts([f"passage: {text}"])
    return vectors[0] if vectors else None
