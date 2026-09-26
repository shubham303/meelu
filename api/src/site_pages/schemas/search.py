from typing import Literal

from pydantic import Field

from src.core.schemas import EntityModel, RequestModel
from src.embed_worker.search.schemas import SearchHit, SearchMode


class SitePageSearchRequest(RequestModel):
    text: str
    input: Literal["query", "text"] = "query"
    mode: SearchMode = "hybrid"
    min_similarity: float | None = Field(default=None, ge=0, le=1)
    limit: int = Field(default=20, ge=1, le=200)
    rerank: bool = True


class SitePageSearchResponse(EntityModel):
    hits: list[SearchHit]
    mode: SearchMode
    reranked: bool
    note: str | None = None
