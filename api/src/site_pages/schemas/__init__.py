from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import inspect

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_pages.models.site_page import SitePage
from src.site_pages.stage import STAGES, page_stage
from src.site_pages.url import normalise_url

PAGE_COLUMN_KEYS = tuple(c.key for c in inspect(SitePage).columns)
PAGE_COLUMNS = tuple(to_camel(key) for key in PAGE_COLUMN_KEYS)

VIEWS = ("slim", "full", "export", "text")
STATUS_CLASSES = ("ok", "error", "gone", "blocked", "serverError", "unreachable", "redirect")
MISSING_FIELDS = ("title", "metaDescription", "h1", "bodyText")
PAGE_SORTS = ("url", "inlinks", "score", "depth", "words", "status", "crawled", "changed")

PAGE_DERIVED = frozenset(
    {
        "id",
        "siteId",
        "userId",
        "seq",
        "createdAt",
        "updatedAt",
        "stage",
        "inlinks",
        "inboundAnchors",
        "depth",
        "linkScore",
        "visited",
    }
)

CRAWL_MAY_NOT_WRITE = frozenset({"inlinks", "inboundAnchors", "depth"})


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _split_csv(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if isinstance(value, list):
        parts = [p.strip() for v in value for p in str(v).split(",")]
        return [p for p in parts if p] or None
    return value


class SitePageFilters(RequestModel):
    url: str | None = None
    urls: list[str] | None = None
    ids: list[str] | None = None
    kind: str | None = None
    kinds: list[str] | None = None
    needs_audit: bool | None = None
    status: Literal[STATUS_CLASSES] | None = None
    status_code: list[int] | None = None
    stage: Literal[STAGES] | None = None
    sort: str | None = None
    url_contains: str | None = None
    title: str | None = None
    title_contains: str | None = None
    meta_contains: str | None = None
    text_contains: str | None = None
    lang: str | None = None
    format: str | None = None
    embed_state: str | None = None
    in_sitemap: bool | None = None
    orphan: bool | None = None
    shallow: bool | None = None
    blocked_by_robots: bool | None = None
    noindex: bool | None = None
    canonical_elsewhere: bool | None = None
    redirects: bool | None = None
    missing: list[Literal[MISSING_FIELDS]] | None = None
    min_words: int | None = None
    max_words: int | None = None
    min_depth: int | None = None
    max_depth: int | None = None
    min_inlinks: int | None = None
    max_inlinks: int | None = None
    crawled_before: datetime | None = None
    crawled_after: datetime | None = None
    changed_before: datetime | None = None
    changed_after: datetime | None = None
    published_before: datetime | None = None
    published_after: datetime | None = None

    @field_validator("urls", "ids", "kinds", "status_code", "missing", mode="before")
    @classmethod
    def _csv(cls, v: Any) -> Any:
        return _split_csv(v)

    @field_validator(
        "crawled_before",
        "crawled_after",
        "changed_before",
        "changed_after",
        "published_before",
        "published_after",
    )
    @classmethod
    def _tz(cls, v: datetime | None) -> datetime | None:
        return _utc(v)

    def sort_specs(self) -> list[tuple[str, str | None]] | None:
        if not self.sort:
            return None
        specs: list[tuple[str, str | None]] = []
        for part in self.sort.split(","):
            bits = part.strip().split(":")
            key = bits[0]
            direction = bits[1] if len(bits) > 1 else None
            if key not in PAGE_SORTS:
                continue
            specs.append((key, direction if direction in ("asc", "desc") else None))
        return specs or None


class SitePageListQuery(SitePageFilters):
    view: Literal[VIEWS] | None = None
    search_text: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)

    def filters(self) -> "SitePageFilters":
        return SitePageFilters.model_validate(
            self.model_dump(exclude={"view", "search_text", "page", "page_size"})
        )

    def paging(self) -> PaginationParams:
        return PaginationParams(page=self.page, page_size=self.page_size).validate()


class SitePageKeywordQuery(SitePageFilters):
    limit: int | None = None

    def filters(self) -> "SitePageFilters":
        return SitePageFilters.model_validate(self.model_dump(exclude={"limit"}))


class SitePageWritableFields(RequestModel):
    url: str | None = None
    status: int | None = None
    content_hash: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    last_crawled_at: datetime | None = None
    title: str | None = None
    title_pixels: int | None = None
    meta_description: str | None = None
    h1: list[str] | None = None
    headings: list[Any] | None = None
    body_text: str | None = None
    out_links: list[Any] | None = None
    external_links: list[Any] | None = None
    canonical: str | None = None
    robots_directives: str | None = None
    x_robots_tag: str | None = None
    blocked_by_robots: bool | None = None
    has_viewport: bool | None = None
    author: str | None = None
    schema_types: list[str] | None = None
    schema_nodes: list[Any] | None = None
    lang: str | None = None
    hreflang: dict[str, Any] | None = None
    kind: str | None = None
    format: str | None = None
    in_sitemap: bool | None = None
    redirect_to: str | None = None
    redirect_final: str | None = None
    redirect_hops: int | None = None
    fetch_error: str | None = None
    content_type: str | None = None
    images: list[Any] | None = None
    published_at: datetime | None = None
    modified_at: datetime | None = None
    content_changed_at: datetime | None = None
    word_count: int | None = None
    mixed_content: bool | None = None
    keywords: list[str] | None = None
    questions_answered: list[str] | None = None
    chunked_from_hash: str | None = None
    embed_state: str | None = None
    embed_error: str | None = None
    shallow: bool | None = None
    shallow_reason: str | None = None

    @field_validator("url", mode="before")
    @classmethod
    def _normalise_url(cls, v: Any) -> Any:
        return normalise_url(v) if isinstance(v, str) else v

    @field_validator("last_crawled_at", "published_at", "modified_at", "content_changed_at")
    @classmethod
    def _tz(cls, v: datetime | None) -> datetime | None:
        return _utc(v)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


def _reject_unwritable(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    known = set(PAGE_COLUMNS) | set(PAGE_COLUMN_KEYS)
    unknown = [k for k in data if k not in known]
    if unknown:
        raise ValueError(f"{', '.join(unknown)} is not part of a page.")
    derived = [k for k in data if to_camel(k) in PAGE_DERIVED]
    if derived:
        raise ValueError(
            f"{', '.join(derived)} cannot be written directly — link-graph numbers are "
            "rebuilt from the stored pages, and visited is the crawl's own sweep mark."
        )
    return data


class SitePageCreateRequest(SitePageWritableFields):
    url: str

    @model_validator(mode="before")
    @classmethod
    def _writable(cls, data: Any) -> Any:
        return _reject_unwritable(data)

    @field_validator("url", mode="before")
    @classmethod
    def _require_url(cls, v: Any) -> str:
        url = normalise_url(v) if isinstance(v, str) else ""
        if not url:
            raise ValueError("A page needs a `url`.")
        return url


class SitePageUpdateRequest(SitePageWritableFields):
    @model_validator(mode="before")
    @classmethod
    def _writable(cls, data: Any) -> Any:
        return _reject_unwritable(data)


class SitePageCrawlItem(SitePageWritableFields):
    url: str

    @model_validator(mode="before")
    @classmethod
    def _drop_graph_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return {k: v for k, v in data.items() if to_camel(k) not in CRAWL_MAY_NOT_WRITE}


class SitePageBatchRequest(RequestModel):
    pages: list[SitePageCrawlItem]


class SitePageVisitedRequest(RequestModel):
    reset: bool = False
    urls: list[str] | None = None


class SitePageMatch(EntityModel):
    text: str
    heading_path: str | None = None


class SemanticMatchFields(EntityModel):
    similarity: float | None = None
    match: SitePageMatch | None = None


class SitePageSlimRecord(SemanticMatchFields):
    id: str
    site_id: str
    chunked_from_hash: str | None
    url: str
    title: str | None
    kind: str
    status: int | None
    inlinks: int
    content_hash: str | None
    shallow: bool
    shallow_reason: str | None
    blocked_by_robots: bool
    last_crawled_at: JsDateTime | None
    embed_state: str | None
    depth: int | None
    word_count: int | None
    content_changed_at: JsDateTime | None
    in_sitemap: bool
    fetch_error: str | None
    redirect_to: str | None

    @computed_field
    @property
    def stage(self) -> str:
        return page_stage(
            self.blocked_by_robots,
            self.status,
            self.shallow,
            self.content_hash,
            self.chunked_from_hash,
        )


class SitePageTextRecord(SemanticMatchFields):
    id: str
    url: str
    title: str | None
    status: int | None
    shallow: bool
    blocked_by_robots: bool
    content_hash: str | None
    chunked_from_hash: str | None
    word_count: int | None
    body_text: str | None

    @computed_field
    @property
    def stage(self) -> str:
        return page_stage(
            self.blocked_by_robots,
            self.status,
            self.shallow,
            self.content_hash,
            self.chunked_from_hash,
            self.body_text is not None,
        )


class SitePageExportRecord(SemanticMatchFields):
    url: str
    status: int | None
    kind: str
    format: str | None
    title: str | None
    title_pixels: int | None
    meta_description: str | None
    h1: list[str]
    lang: str | None
    schema_types: list[str]
    canonical: str | None
    robots_directives: str | None
    x_robots_tag: str | None
    blocked_by_robots: bool
    has_viewport: bool | None
    word_count: int | None
    inlinks: int
    depth: int | None
    in_sitemap: bool
    shallow: bool
    shallow_reason: str | None
    redirect_to: str | None
    redirect_hops: int | None
    fetch_error: str | None
    content_type: str | None
    published_at: JsDateTime | None
    modified_at: JsDateTime | None
    content_changed_at: JsDateTime | None
    last_crawled_at: JsDateTime | None
    embed_state: str | None
    content_hash: str | None
    chunked_from_hash: str | None
    has_text: bool
    out_link_count: int
    external_link_count: int
    image_count: int
    image_bytes: int
    heading_count: int

    @computed_field
    @property
    def stage(self) -> str:
        return page_stage(
            self.blocked_by_robots,
            self.status,
            self.shallow,
            self.content_hash,
            self.chunked_from_hash,
        )


class SitePageRecord(SemanticMatchFields):
    id: str
    site_id: str
    created_at: JsDateTime
    updated_at: JsDateTime
    url: str
    status: int | None
    content_hash: str | None
    etag: str | None
    last_modified: str | None
    last_crawled_at: JsDateTime | None
    inlinks: int
    inbound_anchors: list[Any]
    title: str | None
    title_pixels: int | None
    meta_description: str | None
    h1: list[str]
    headings: list[Any]
    body_text: str | None
    out_links: list[Any]
    external_links: list[Any]
    canonical: str | None
    robots_directives: str | None
    x_robots_tag: str | None
    blocked_by_robots: bool
    has_viewport: bool | None
    author: str | None
    schema_types: list[str]
    schema_nodes: list[Any]
    lang: str | None
    hreflang: dict[str, Any]
    kind: str
    format: str | None
    in_sitemap: bool
    depth: int | None
    redirect_to: str | None
    redirect_final: str | None
    redirect_hops: int | None
    fetch_error: str | None
    content_type: str | None
    images: list[Any]
    published_at: JsDateTime | None
    modified_at: JsDateTime | None
    content_changed_at: JsDateTime | None
    word_count: int | None
    mixed_content: bool
    keywords: list[str]
    questions_answered: list[str]
    link_score: float | None
    chunked_from_hash: str | None
    embed_state: str | None
    embed_error: str | None
    shallow: bool
    shallow_reason: str | None
    visited: bool
    index_state: str | None = None
    coverage_state: str | None = None
    google_canonical: str | None = None
    index_checked_at: JsDateTime | None = None

    @computed_field
    @property
    def stage(self) -> str:
        return page_stage(
            self.blocked_by_robots,
            self.status,
            self.shallow,
            self.content_hash,
            self.chunked_from_hash,
            self.body_text is not None,
        )


SitePageViewRecord = SitePageSlimRecord | SitePageTextRecord | SitePageExportRecord | SitePageRecord


class SitePageListResult(PaginatedApiResponse[SitePageViewRecord]):
    note: str | None = None


class SitePageRef(EntityModel):
    id: str
    url: str


class SitePageEdge(EntityModel):
    src: str
    dst: str


class SitePageLandingSeed(EntityModel):
    sessions_by_path: dict[str, int]


class SemanticPageMatch(EntityModel):
    page_id: str
    similarity: float
    snippet: str
    heading_path: str | None


class CrawlKnownPageRecord(EntityModel):
    url: str
    inlinks: int
    crawl_complete: bool
    content_hash: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    last_crawled_at: JsDateTime | None = None


class SitemapPresenceResult(EntityModel):
    known: int
    listed: int


class CrawlCountsResult(EntityModel):
    pages: int


class TermCount(EntityModel):
    value: str
    pages: int


class SitePageKeywordCoverageResult(EntityModel):
    keywords: list[TermCount]
    questions: list[TermCount]
    keywords_truncated: bool
    questions_truncated: bool
    matched_pages: int
    annotated_pages: int


class StageCount(EntityModel):
    stage: str
    n: int


class KindCount(EntityModel):
    kind: str
    n: int


class ShallowReasonCount(EntityModel):
    reason: str | None
    n: int


class ChunkCounts(EntityModel):
    total: int
    embedded: int
    failed: int


class SitePageStatsRecord(EntityModel):
    pages: int
    blocked_by_robots: int
    blocked_and_discoverable: int
    ok: int
    errored: int
    gone: int
    not_in_sitemap: int
    sitemap_missing: int
    not_found: int
    blocked: int
    server_error: int
    unreachable: int
    orphans: int
    shallow: int
    embed_failed: int
    crawl_complete: int
    by_stage: list[StageCount]
    by_kind: list[KindCount]
    by_shallow_reason: list[ShallowReasonCount]
    chunks: ChunkCounts


class SitePageStatsResult(SitePageStatsRecord):
    last_crawled_at: JsDateTime | None = None
    sitemap_url_count: int | None = None


class SiteChunkRecord(EntityModel):
    id: str
    site_id: str
    page_id: str
    ordinal: int
    heading_path: str | None
    text: str
    embed_model: str | None
    embedded_from_hash: str | None
    embed_attempts: int
    embed_error: str | None
    chunk_strategy: str | None
    from_hash: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class SitePageBatchResult(EntityModel):
    pages: int


class SitePageVisitSweepResult(EntityModel):
    reset: int


class SitePageVisitedResult(EntityModel):
    visited: int


class SitePagePruneResult(EntityModel):
    deleted: int


class SitePageGraphResult(EntityModel):
    rebuilt: bool = Field(default=True)


class SitePageSlimListItemResponse(SitePageSlimRecord):
    pass


class SitePageTextListItemResponse(SitePageTextRecord):
    pass


class SitePageExportListItemResponse(SitePageExportRecord):
    pass


class SitePageResponse(SitePageRecord):
    pass


SitePageListItemResponse = (
    SitePageSlimListItemResponse
    | SitePageTextListItemResponse
    | SitePageExportListItemResponse
    | SitePageResponse
)


class SitePageListResponse(PaginatedApiResponse[SitePageListItemResponse]):
    note: str | None = None


class SitePageDeleteResponse(EntityModel):
    id: str
    url: str
    deleted: bool = Field(default=True)


class SitePageKeywordCoverageResponse(SitePageKeywordCoverageResult):
    pass


class SitePageStatsResponse(SitePageStatsResult):
    pass


class SiteChunkResponse(SiteChunkRecord):
    pass
