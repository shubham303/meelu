from typing import Literal

from src.core.schemas import EntityModel

SEARCH_MODES = ("keyword", "semantic", "hybrid")
SearchMode = Literal["keyword", "semantic", "hybrid"]


class SearchHit(EntityModel):
    page_id: str
    url: str
    title: str | None
    chunk_id: str | None
    heading_path: str | None
    snippet: str | None
    score: float
    similarity: float | None = None
    keyword_rank: int | None = None
    rerank_score: float | None = None


class SearchResult(EntityModel):
    hits: list[SearchHit]
    mode: SearchMode
    reranked: bool
    note: str | None = None
