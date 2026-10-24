from datetime import datetime
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.pagination import PaginatedApiResponse
from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_pages.schemas import CrawlKnownPageRecord

CRAWL_JOB_STATUSES = ("queued", "running", "cancelling", "cancelled", "completed", "failed")
ACTIVE_JOB_STATUSES = ("queued", "running", "cancelling")
SETTLED_JOB_STATUSES = ("completed", "failed", "cancelled")

CrawlJobSort = Literal["created", "started", "finished", "fetched"]


def _strings(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("must be a list of strings.")
    return [str(u) for u in value if str(u).strip() != ""]


class CrawlJobFilters(BaseModel):
    statuses: list[str] | None = None
    trigger: str | None = None
    active: bool | None = None
    complete: bool | None = None
    failed: bool | None = None
    started_after: datetime | None = None
    started_before: datetime | None = None
    finished_after: datetime | None = None
    finished_before: datetime | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    sort: CrawlJobSort | None = None


class CrawlJobRecord(EntityModel):
    keep_null: ClassVar[frozenset[str]] = frozenset({"finishedAt", "error"})

    id: str
    site_id: str
    status: str
    trigger: str
    sitemap_urls: list[str]
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    discovered: int
    fetched: int
    queued: int
    new_pages: int
    changed: int
    unchanged: int
    failed: int
    pages_stored: int
    passages_stored: int
    complete: bool
    error: str | None = None
    stop_reason: str | None = None
    notes: list[Any]
    created_at: JsDateTime
    updated_at: JsDateTime


class CrawlJobResponse(CrawlJobRecord):
    pass


class CrawlJobListItemResponse(CrawlJobRecord):
    pass


class CrawlJobCreateRequest(RequestModel):
    trigger: str = "api"
    sitemap_urls: list[str] | None = None
    reap: bool = False
    stale_ms: float | None = None

    @field_validator("sitemap_urls", mode="before")
    @classmethod
    def _validate_sitemap_urls(cls, v: Any) -> list[str] | None:
        return _strings(v)


class CrawlJobReapRequest(RequestModel):
    stale_ms: float | None = None


class CrawlJobUpdateRequest(RequestModel):
    status: str | None = None
    heartbeat: bool | None = None
    reason: str | None = None
    discovered: int | None = None
    fetched: int | None = None
    queued: int | None = None
    new_pages: int | None = None
    changed: int | None = None
    unchanged: int | None = None
    failed: int | None = None
    pages_stored: int | None = None
    complete: bool | None = None
    notes: list[str] | None = None
    error: str | None = None
    sitemap_urls: list[str] | None = None
    frontier: list[str] | None = None
    sitemap_complete: bool | None = None
    sitemaps_used: list[str] | None = None
    sitemap_at_root: bool | None = None
    sitemaps_listing_sitemaps: list[str] | None = None
    sitemap_url_count: int | None = None
    robots_txt: str | None = None
    llms_txt: str | None = None
    robots_status: int | None = None
    llms_status: int | None = None
    robots_fetched_at: datetime | None = None
    llms_fetched_at: datetime | None = None
    crawler_access: dict[str, Any] | None = None
    host_variants: dict[str, Any] | None = None

    @field_validator(
        "notes", "sitemap_urls", "sitemaps_used", "sitemaps_listing_sitemaps", "frontier", mode="before"
    )
    @classmethod
    def _validate_lists(cls, v: Any) -> list[str] | None:
        return None if v is None else [str(u) for u in v]

    @field_validator("error", mode="before")
    @classmethod
    def _validate_error(cls, v: Any) -> str | None:
        return None if v is None else str(v)[:500]

    def counters(self, keys: tuple[str, ...]) -> dict[str, int]:
        return self.model_dump(by_alias=True, include=set(keys), exclude_none=True)

    def given(self, field: str) -> bool:
        return field in self.model_fields_set


class CrawlTargetResponse(EntityModel):
    site_id: str
    domain: str
    name: str


class CrawlPlanResponse(EntityModel):
    job: CrawlJobResponse
    target: CrawlTargetResponse
    sitemap_urls: list[str]
    concurrency: int
    batch_size: int
    known: list[CrawlKnownPageRecord]
    link_frontier: list[str]


class CrawlJobStartResponse(EntityModel):
    started: bool
    job: CrawlJobResponse | None = None
    plan: CrawlPlanResponse | None = None
    reaped: list[CrawlJobResponse] = Field(default_factory=list)
    reason: str | None = None


class CrawlJobReapResponse(EntityModel):
    reaped: int
    jobs: list[CrawlJobResponse]
    note: str


class CrawlJobHeartbeatResponse(EntityModel):
    stop: bool


class CrawlJobDeleteResponse(EntityModel):
    id: str
    stopped: bool
    deleted: bool
    job: CrawlJobResponse | None = None


class CrawlStatusResponse(EntityModel):
    site_id: str
    domain: str
    job_id: str | None = None
    state: str
    active: bool
    trigger: str | None = None
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    fetched: int = 0
    queued: int = 0
    discovered: int = 0
    error: str | None = None
    stop_reason: str | None = None
    last_crawled_at: JsDateTime | None = None
    last_crawl_complete: bool = False
    sitemap_urls: list[str]
    pages: int


class CrawlJobListResponse(PaginatedApiResponse[CrawlJobListItemResponse]):
    status: CrawlStatusResponse
