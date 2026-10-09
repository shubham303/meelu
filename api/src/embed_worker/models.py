import asyncio
import threading
from collections.abc import Callable
from typing import Generic, TypeVar

from src.core.logging import get_logger
from src.embed_worker.settings import search_settings

log = get_logger("embed_worker.models")

T = TypeVar("T")


class LazyModel(Generic[T]):
    def __init__(self, name: str, enabled: Callable[[], bool], load: Callable[[], T]):
        self.name = name
        self._enabled = enabled
        self._load = load
        self._lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._loaded = False
        self._instance: T | None = None

    def get(self) -> T | None:
        if not self._enabled():
            return None
        if self._loaded:
            return self._instance
        with self._lock:
            if self._loaded:
                return self._instance
            try:
                self._instance = self._load()
            except Exception as e:
                log.error("model_unavailable", model=self.name, error=str(e))
                self._instance = None
            self._loaded = True
        return self._instance

    def run(self, fn: Callable[[T], object]):
        instance = self.get()
        if instance is None:
            return None
        with self._run_lock:
            return fn(instance)

    def reset(self) -> None:
        with self._lock:
            self._loaded = False
            self._instance = None


def _load_embedder():
    from src.embed_worker.embedding import Embedder

    settings = search_settings()
    return Embedder(settings.meelu_embed_model, settings.meelu_onnx_threads)


def _load_reranker():
    from src.embed_worker.reranker import Reranker

    settings = search_settings()
    return Reranker(settings.meelu_rerank_model, settings.meelu_onnx_threads)


embedder = LazyModel(
    "embedder", lambda: search_settings().meelu_embed_disabled != "1", _load_embedder
)
reranker = LazyModel(
    "reranker", lambda: search_settings().meelu_rerank_disabled != "1", _load_reranker
)


def embed_model() -> str:
    return search_settings().meelu_embed_model


def rerank_model() -> str:
    return search_settings().meelu_rerank_model


async def embed_texts(inputs: list[str]) -> list[list[float]] | None:
    if not inputs:
        return []
    return await asyncio.to_thread(embedder.run, lambda m: m.embed(inputs))


async def embed_query(q: str) -> list[float] | None:
    vectors = await embed_texts([f"query: {q}"])
    return vectors[0] if vectors else None


async def embed_passage(text: str) -> list[float] | None:
    vectors = await embed_texts([f"passage: {text}"])
    return vectors[0] if vectors else None


async def rerank(query: str, documents: list[str]) -> list[float] | None:
    if not documents:
        return []
    return await asyncio.to_thread(reranker.run, lambda m: m.score(query, documents))
