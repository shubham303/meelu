from sqlalchemy.ext.asyncio import AsyncSession

from src.embed_worker import models
from src.embed_worker.search import repository as repo
from src.embed_worker.search.schemas import SearchHit, SearchMode, SearchResult
from src.embed_worker.settings import search_settings

RERANK_POOL_FACTOR = 4
MAX_LIMIT = 200


def default_min_similarity() -> float:
    return search_settings().meelu_search_min_similarity


def _coverage_note(mode: SearchMode, wanted: SearchMode, total: int, embedded: int) -> str | None:
    if wanted != "keyword" and mode == "keyword":
        return "Keyword search only — the embedding model is unavailable."
    if mode == "keyword":
        return None
    if total == 0:
        return "Nothing is embedded for this website yet, so a semantic search cannot see any page."
    if embedded < total:
        return f"Semantic coverage is partial: {embedded} of {total} passages embedded."
    return None


async def _search(
    db: AsyncSession,
    site_id: str,
    text: str,
    *,
    embed_input: str,
    keyword_as_terms: bool,
    mode: SearchMode,
    min_similarity: float | None,
    limit: int,
    rerank: bool,
) -> SearchResult:
    text = text.strip()
    if not text:
        return SearchResult(hits=[], mode=mode, reranked=False)

    limit = min(max(limit, 1), MAX_LIMIT)
    threshold = default_min_similarity() if min_similarity is None else min_similarity

    vector = None
    ran: SearchMode = mode
    if mode != "keyword":
        vectors = await models.embed_texts([embed_input])
        vector = vectors[0] if vectors else None
        if vector is None:
            if mode == "semantic":
                return SearchResult(
                    hits=[],
                    mode=mode,
                    reranked=False,
                    note="Semantic search is unavailable — the text could not be embedded.",
                )
            ran = "keyword"

    pool = limit * RERANK_POOL_FACTOR if rerank else limit
    rows = await repo.fused_page_hits(
        db,
        site_id,
        keyword=text if ran != "semantic" else None,
        keyword_as_terms=keyword_as_terms,
        embedding=vector,
        model=models.embed_model(),
        min_similarity=threshold,
        pool=max(pool * 2, 50),
        limit=pool,
    )
    hits = [SearchHit(**r) for r in rows]

    reranked = False
    if rerank and hits:
        scores = await models.rerank(text, [h.snippet or h.title or h.url for h in hits])
        if scores is not None:
            for hit, score in zip(hits, scores):
                hit.rerank_score = score
            hits.sort(key=lambda h: h.rerank_score or 0.0, reverse=True)
            reranked = True
    hits = hits[:limit]

    total, embedded = await repo.chunk_coverage(db, site_id)
    return SearchResult(
        hits=hits, mode=ran, reranked=reranked, note=_coverage_note(ran, mode, total, embedded)
    )


async def search_from_query(
    db: AsyncSession,
    site_id: str,
    query: str,
    *,
    mode: SearchMode = "hybrid",
    min_similarity: float | None = None,
    limit: int = 20,
    rerank: bool = True,
) -> SearchResult:
    return await _search(
        db,
        site_id,
        query,
        embed_input=f"query: {query.strip()}",
        keyword_as_terms=False,
        mode=mode,
        min_similarity=min_similarity,
        limit=limit,
        rerank=rerank,
    )


async def search_from_text(
    db: AsyncSession,
    site_id: str,
    text: str,
    *,
    mode: SearchMode = "hybrid",
    min_similarity: float | None = None,
    limit: int = 20,
    rerank: bool = True,
) -> SearchResult:
    return await _search(
        db,
        site_id,
        text,
        embed_input=f"passage: {text.strip()}",
        keyword_as_terms=True,
        mode=mode,
        min_similarity=min_similarity,
        limit=limit,
        rerank=rerank,
    )
