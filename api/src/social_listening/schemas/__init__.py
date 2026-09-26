from datetime import datetime
from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

POST_STATUSES = ("fetched", "matched", "needs_reply", "drafted", "replied", "skipped", "filtered")
POST_KINDS = ("topic", "brand", "competitor")
TARGET_KINDS = ("brand", "competitor")
RUN_STATUSES = ("running", "done", "stopped", "error")
POST_SORTS = ("best", "newest", "engaged", "similarity")
MENTION_CLASSES = ("praise", "complaint", "feature_request", "question", "switch_opportunity")


class ConfigUpdateRequest(RequestModel):
    platforms: list[str] | None = None
    results_per_keyword: int | None = None
    min_relevance: float | None = None
    min_similarity: float | None = None
    max_age_days: int | None = None
    drop_dead_posts: bool | None = None
    schedule: str | None = None

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


class TargetUpsertItem(RequestModel):
    kind: str
    name: str
    enabled: bool = True
    source: str = "user"


class TargetPatchRequest(RequestModel):
    name: str | None = None
    enabled: bool | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RunUpdateRequest(RequestModel):
    status: str | None = None
    finished_at: datetime | None = None
    fetched_count: int | None = None
    kept_count: int | None = None
    platform_stats: dict[str, Any] | None = None
    error: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class PostUpsertItem(RequestModel):
    url: str
    platform: str
    kind: str
    title: str | None = None
    text: str | None = None
    author_handle: str | None = None
    author_name: str | None = None
    posted_at: datetime | None = None
    engagement: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    matched_targets: list[str] = Field(default_factory=list)
    intent: str | None = None
    sentiment: str | None = None
    is_question: bool | None = None
    classes: list[str] = Field(default_factory=list)
    relevance: float | None = None
    composite_score: float | None = None
    keep_reason: str | None = None
    suggested_angle: str | None = None
    status: str | None = None
    query_id: str | None = None


class PostClassifyItem(RequestModel):
    id: str
    status: str
    intent: str | None = None
    sentiment: str | None = None
    is_question: bool | None = None
    classes: list[str] = Field(default_factory=list)
    relevance: float | None = None
    composite_score: float | None = None
    keep_reason: str | None = None


class KnownUrlsRequest(RequestModel):
    urls: list[str]


class PostsBulkRequest(RequestModel):
    run_id: str | None = None
    posts: list[PostUpsertItem]


class PostsClassifyRequest(RequestModel):
    posts: list[PostClassifyItem]


class PostPatchRequest(RequestModel):
    status: str | None = None
    reply_text: str | None = None
    suggested_angle: str | None = None
    classes: list[str] | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class PostFilters(RequestModel):
    kind: str | None = None
    status: str | None = None
    platform: str | None = None
    intent: str | None = None
    sentiment: str | None = None
    cls: str | None = None
    target: str | None = None
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
    min_relevance: float
    min_similarity: float
    max_age_days: int
    drop_dead_posts: bool
    schedule: str | None = None
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
    created_at: JsDateTime
    updated_at: JsDateTime


class QueryEmbeddingInput(EntityModel):
    id: str
    text: str


class PostEmbeddingInput(EntityModel):
    id: str
    title: str | None = None
    text: str | None = None


class TargetResponse(EntityModel):
    id: str
    site_id: str
    kind: str
    name: str
    enabled: bool
    source: str
    created_at: JsDateTime
    updated_at: JsDateTime


class RunResponse(EntityModel):
    id: str
    site_id: str
    status: str
    started_at: JsDateTime
    finished_at: JsDateTime | None = None
    fetched_count: int
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
    kind: str
    title: str | None = None
    text: str | None = None
    author_handle: str | None = None
    author_name: str | None = None
    posted_at: JsDateTime | None = None
    engagement: dict[str, Any]
    context: dict[str, Any]
    matched_targets: list[str]
    intent: str | None = None
    sentiment: str | None = None
    is_question: bool | None = None
    classes: list[str]
    relevance: float | None = None
    composite_score: float | None = None
    keep_reason: str | None = None
    suggested_angle: str | None = None
    status: str
    similarity: float | None = None
    query_id: str | None = None
    reply_text: str | None = None
    replied_at: JsDateTime | None = None
    run_id: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class GateResponse(EntityModel):
    pending: int
    scored: int
    kept: int
    filtered: int


class BulkUpsertResponse(EntityModel):
    inserted: int
    updated: int


class DeleteResponse(EntityModel):
    id: str


class KeptQueryCount(EntityModel):
    id: str
    text: str
    kept: int


class MentionClassCounts(EntityModel):
    praise: int
    complaint: int
    feature_request: int
    question: int
    switch_opportunity: int


class SentimentCounts(EntityModel):
    positive: int
    neutral: int
    negative: int


class SummaryResponse(EntityModel):
    needs_reply: int
    drafted: int
    replied: int
    skipped: int
    brand_mentions: int
    competitor_mentions: int
    unprocessed: int
    last_run: RunResponse | None = None
    kept_by_query: list[KeptQueryCount]
    mention_classes: MentionClassCounts
    sentiment: SentimentCounts
