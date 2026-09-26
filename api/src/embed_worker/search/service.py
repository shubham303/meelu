import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.embed_worker import models
from src.embed_worker.search.schemas import SearchHit, SearchMode, SearchResult
from src.embed_worker.settings import search_settings
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import ChunkHit

RERANK_POOL_FACTOR = 4
MAX_LIMIT = 200
RRF_K = 60
MAX_TEXT_TERMS = 32

TOKEN_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


def or_tsquery_terms(source: str) -> str:
    seen: dict[str, None] = {}
    for token in TOKEN_RE.findall(source.lower()):
        if token not in seen:
            seen[token] = None
        if len(seen) >= MAX_TEXT_TERMS:
            break
    return " | ".join(seen)


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


class PageSearchService:
    def default_min_similarity(self) -> float:
        return search_settings().meelu_search_min_similarity

    async def search_from_query(
        self,
        db: AsyncSession,
        site_id: str,
        query: str,
        *,
        mode: SearchMode = "hybrid",
        min_similarity: float | None = None,
        limit: int = 20,
        rerank: bool = True,
    ) -> SearchResult:
        return await self._search(
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
        self,
        db: AsyncSession,
        site_id: str,
        text: str,
        *,
        mode: SearchMode = "hybrid",
        min_similarity: float | None = None,
        limit: int = 20,
        rerank: bool = True,
    ) -> SearchResult:
        return await self._search(
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

    async def _search(
        self,
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
        threshold = self.default_min_similarity() if min_similarity is None else min_similarity

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
        hits = await self._fused_page_hits(
            db,
            site_id,
            keyword=text if ran != "semantic" else None,
            keyword_as_terms=keyword_as_terms,
            embedding=vector,
            min_similarity=threshold,
            pool=max(pool * 2, 50),
            limit=pool,
        )

        reranked = False
        if rerank and hits:
            scores = await models.rerank(text, [h.snippet or h.title or h.url for h in hits])
            if scores is not None:
                for hit, score in zip(hits, scores):
                    hit.rerank_score = score
                hits.sort(key=lambda h: h.rerank_score or 0.0, reverse=True)
                reranked = True
        hits = hits[:limit]

        coverage = await site_chunks.counts(db, site_id)
        return SearchResult(
            hits=hits,
            mode=ran,
            reranked=reranked,
            note=_coverage_note(ran, mode, coverage.total, coverage.embedded),
        )

    async def _fused_page_hits(
        self,
        db: AsyncSession,
        site_id: str,
        *,
        keyword: str | None,
        keyword_as_terms: bool,
        embedding: list[float] | None,
        min_similarity: float,
        pool: int,
        limit: int,
    ) -> list[SearchHit]:
        keyword_hits: list[ChunkHit] = []
        if keyword:
            if keyword_as_terms:
                terms = or_tsquery_terms(keyword)
                if terms:
                    keyword_hits = await site_chunks.keyword_hits(db, site_id, terms, True, pool)
            else:
                keyword_hits = await site_chunks.keyword_hits(db, site_id, keyword, False, pool)

        semantic_hits: list[ChunkHit] = []
        if embedding is not None:
            semantic_hits = await site_chunks.semantic_hits(
                db, site_id, embedding, models.embed_model(), min_similarity, pool
            )

        if not keyword_hits and not semantic_hits:
            return []

        scores: dict[str, float] = {}
        similarity: dict[str, float] = {}
        keyword_rank: dict[str, int] = {}
        best: dict[str, ChunkHit] = {}
        for rank, hit in enumerate(keyword_hits, start=1):
            scores[hit.page_id] = scores.get(hit.page_id, 0.0) + 1.0 / (RRF_K + rank)
            keyword_rank.setdefault(hit.page_id, rank)
            best.setdefault(hit.page_id, hit)
        for rank, hit in enumerate(semantic_hits, start=1):
            scores[hit.page_id] = scores.get(hit.page_id, 0.0) + 1.0 / (RRF_K + rank)
            similarity[hit.page_id] = max(similarity.get(hit.page_id, hit.raw), hit.raw)
            best[hit.page_id] = hit

        pages = {p.id: p for p in await site_pages.list_by_ids(db, site_id, list(scores))}
        ranked = sorted(
            (page_id for page_id in scores if page_id in pages),
            key=lambda page_id: (
                -scores[page_id],
                similarity.get(page_id) is None,
                -(similarity.get(page_id) or 0.0),
            ),
        )
        return [
            SearchHit(
                page_id=page_id,
                url=pages[page_id].url,
                title=pages[page_id].title,
                score=scores[page_id],
                similarity=similarity.get(page_id),
                keyword_rank=keyword_rank.get(page_id),
                chunk_id=best[page_id].id,
                heading_path=best[page_id].heading_path,
                snippet=best[page_id].text,
            )
            for page_id in ranked[:limit]
        ]


page_search_service = PageSearchService()
