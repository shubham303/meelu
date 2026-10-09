from datetime import datetime
from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

PIPELINE_STATUSES = ("fetched", "matched", "dropped")
USER_STATUSES = ("to_reply", "drafted", "replied", "skipped", "rejected")
POST_STATUSES = PIPELINE_STATUSES + USER_STATUSES
DONE_STATUSES = ("replied", "skipped", "rejected")
DROP_REASONS = (
    "too_old",
    "excluded_word",
    "far_in_meaning",
    "judged_off_topic",
    "dead",
    "duplicate",
    "unembeddable",
    "line_removed",
)
INGEST_DROP_REASONS = ("too_old", "excluded_word")
JUDGE_DROP_REASONS = ("judged_off_topic", "dead")
JUDGE_STATUSES = ("to_reply", "dropped")
RUN_STATUSES = ("running", "done", "stopped", "error")
POST_SORTS = ("best", "newest", "engaged", "similarity")
STRICTNESS_THRESHOLDS = {
    "loose": (0.75, 0.45),
    "balanced": (0.8, 0.6),
    "strict": (0.85, 0.75),
}


class ConfigUpdateRequest(RequestModel):
    platforms: list[str] | None = None
    results_per_keyword: int | None = None
    strictness: str | None = None
    max_age_days: int | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class QueryUpsertItem(RequestModel):
    text: str
    enabled: bool = True
    source: str = "user"


class QueryPatchRequest(RequestModel):
    text: str | None = None
    enabled: bool | None = None
    keywords: list[str] | None = None
    negative_keywords: list[str] | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RunUpdateRequest(RequestModel):
    status: str | None = None
    finished_at: datetime | None = None
    fetched_count: int | None = None
    matched_count: int | None = None
    kept_count: int | None = None
    platform_stats: dict[str, Any] | None = None
    error: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class PostIngestItem(RequestModel):
    url: str
    platform: str
    external_id: str | None = None
    title: str | None = None
    text: str | None = None
    author_handle: str | None = None
    author_name: str | None = None
    posted_at: datetime | None = None
    engagement: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    query_id: str | None = None
    drop_reason: str | None = None


class PostsBulkRequest(RequestModel):
    run_id: str | None = None
    posts: list[PostIngestItem]


class PostJudgeItem(RequestModel):
    id: str
    status: str
    drop_reason: str | None = None
    relevance: float | None = None
    composite_score: float | None = None
    keep_reason: str | None = None
    suggested_angle: str | None = None


class PostsJudgeRequest(RequestModel):
    posts: list[PostJudgeItem]


class PostPatchRequest(RequestModel):
    status: str | None = None
    reply_text: str | None = None
    suggested_angle: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class PostFilters(RequestModel):
    statuses: list[str] | None = None
    platform: str | None = None
    query_id: str | None = None
    run_id: str | None = None
    min_relevance: float | None = None
    q: str | None = None
    sort: str | None = None


class ConfigResponse(EntityModel):
    id: str
    site_id: str
    platforms: list[str]
    results_per_keyword: int
    strictness: str
    max_age_days: int
    min_similarity: float
    min_relevance: float
    created_at: JsDateTime
    updated_at: JsDateTime


class QueryResponse(EntityModel):
    id: str
    site_id: str
    text: str
    enabled: bool
    source: str
    keywords: list[str]
    negative_keywords: list[str]
    embedded: bool
    found: int
    kept: int
    created_at: JsDateTime
    updated_at: JsDateTime


class QueryEmbeddingInput(EntityModel):
    id: str
    text: str


class PostEmbeddingInput(EntityModel):
    id: str
    title: str | None = None
    text: str | None = None


class RunResponse(EntityModel):
    id: str
    site_id: str
    status: str
    started_at: JsDateTime
    finished_at: JsDateTime | None = None
    fetched_count: int
    matched_count: int
    kept_count: int
    platform_stats: dict[str, Any]
    error: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class PostResponse(EntityModel):
    id: str
    site_id: str
    url: str
    platform: str
    external_id: str | None = None
    title: str | None = None
    text: str | None = None
    author_handle: str | None = None
    author_name: str | None = None
    posted_at: JsDateTime | None = None
    engagement: dict[str, Any]
    context: dict[str, Any]
    status: str
    drop_reason: str | None = None
    similarity: float | None = None
    relevance: float | None = None
    composite_score: float | None = None
    keep_reason: str | None = None
    suggested_angle: str | None = None
    reply_text: str | None = None
    replied_at: JsDateTime | None = None
    query_id: str | None = None
    run_id: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class GateResponse(EntityModel):
    pending: int
    scored: int
    kept: int
    dropped: int


class BulkInsertResponse(EntityModel):
    inserted: int
    known: int
    duplicates: int


class UpsertResponse(EntityModel):
    inserted: int
    updated: int


class JudgeResponse(EntityModel):
    updated: int


class DeleteResponse(EntityModel):
    id: str


class SummaryResponse(EntityModel):
    to_reply: int
    drafted: int
    replied: int
    skipped: int
    rejected: int
    done: int
    unprocessed: int
    last_run: RunResponse | None = None
