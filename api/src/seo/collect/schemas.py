from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel, RequestModel


class CollectResult(EntityModel):
    added: int = 0
    refreshed: int = 0
    skipped: int = 0
    embedded: int = 0
    vendor_calls: int = 0
    spent_micros: int = 0
    cache_hits: int = 0
    competitors: list[str] = Field(default_factory=list)
    plan: dict[str, Any] | None = None


class CollectKeywordsRequest(RequestModel):
    job_id: str
    seeds: list[str] | None = None
    keyword_ids: list[str] | None = None
    source_table: str | None = None
    from_gsc: bool = True
    from_ranked: bool = True
    max_seeds: int = 10
    ideas_per_seed: int = 30
    dry_run: bool = False


class CollectCompetitorsRequest(RequestModel):
    job_id: str
    limit: int = 10
    keyword_ids: list[str] | None = None


class CollectCompetitorKeywordsRequest(RequestModel):
    job_id: str
    competitor_ids: list[str] | None = None
    limit: int = 300


class CollectSerpsRequest(RequestModel):
    job_id: str
    keyword_ids: list[str] | None = None
    terms: list[str] | None = None
    suggestion_ids: list[str] | None = None
    source_table: str | None = None
    device: str = "desktop"
    max_keywords: int = 30
