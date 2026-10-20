from typing import Any

from src.core.schemas import EntityModel, JsDateTime, RequestModel

PIPELINE_STATUSES = ("candidate", "matched")
USER_STATUSES = ("to_reply", "drafted", "replied", "skipped", "rejected")
POST_STATUSES = PIPELINE_STATUSES + USER_STATUSES
DONE_STATUSES = ("replied", "skipped", "rejected")
RUN_STATUSES = ("running", "done", "stopped", "error")
COLLECT_STATUSES = ("running", "done", "error")
MIN_SIMILARITY = 0.75
KEYWORDS_PER_LINE = 2
MAX_LINES_PER_SITE = 30
PER_KEYWORD = 25
LOOKBACK_DAYS = 7
MINIMUM_BALANCE_USD = 5


class ConfigUpdateRequest(RequestModel):
    platforms: list[str] | None = None

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

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RunUpdateRequest(RequestModel):
    status: str | None = None
    matched_count: int | None = None
    kept_count: int | None = None
    error: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class CollectRequest(RequestModel):
    platform: str


class PostVerdict(RequestModel):
    id: str
    keep: bool
    keep_reason: str | None = None
    suggested_angle: str | None = None


class PostsJudgeRequest(RequestModel):
    posts: list[PostVerdict]


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
    q: str | None = None


class ConfigResponse(EntityModel):
    id: str
    site_id: str
    platforms: list[str]
    created_at: JsDateTime
    updated_at: JsDateTime


class QueryResponse(EntityModel):
    id: str
    site_id: str
    text: str
    enabled: bool
    source: str
    keywords: list[str]
    embedded: bool
    found: int
    kept: int
    created_at: JsDateTime
    updated_at: JsDateTime


class QueryEmbeddingInput(EntityModel):
    id: str
    text: str


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


class PlatformEstimate(EntityModel):
    platform: str
    keywords: int
    vendor_keywords: int
    max_cost_micros: int | None


class EstimateResponse(EntityModel):
    platforms: list[PlatformEstimate]


class PostResponse(EntityModel):
    id: str
    site_id: str
    post_id: str
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
    similarity: float | None = None
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
    matched: int
    removed: int


class UpsertResponse(EntityModel):
    inserted: int
    updated: int


class JudgeResponse(EntityModel):
    kept: int
    removed: int


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
