from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.schemas import fields


class SeoJobRecord(EntityModel):
    id: str
    site_id: str
    prompt: str
    status: str
    vendor_calls: int
    vendor_micros: int
    vendor_ceiling_micros: int
    created_at: JsDateTime
    updated_at: JsDateTime


class SeoJobCreateRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class SeoJobUpdateRequest(RequestModel):
    status: str = Field(default="", validate_default=True)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> str:
        return fields.status(value)


class SiteStateRecord(EntityModel):
    id: str
    site_id: str
    location_code: int
    language_code: str
    brand_terms: list[str]
    precompute_requested_at: JsDateTime | None
    rollup_at: JsDateTime | None
    embedded_at: JsDateTime | None
    ctr_curve: dict[str, Any]


class SiteStateUpdateRequest(RequestModel):
    location_code: int | None = None
    language_code: str | None = None
    brand_terms: list[str] | None = None

    @field_validator("brand_terms", mode="before")
    @classmethod
    def _brand_terms(cls, value: Any) -> list[str] | None:
        return None if value is None else fields.brand_terms(value)

    @field_validator("language_code", mode="before")
    @classmethod
    def _language(cls, value: Any) -> str | None:
        return None if value is None else str(value).strip().lower()[:8]


class PageFactsRecord(EntityModel):
    id: str
    page_id: str
    url: str
    status: int | None
    redirect_to: str | None
    page_type: str | None
    lang: str | None
    title: str | None
    h1: str | None
    headings: list[str]
    meta_description: str | None
    title_pixels: int | None
    word_count: int | None
    inlinks: int
    link_score: float | None
    published_at: JsDateTime | None
    first_seen_at: JsDateTime | None
    content_hash: str | None
    indexable: bool
    live: bool
    is_home: bool
    impressions_28d: int
    clicks_28d: int
    impressions_ly_28d: int | None
    clicks_ly_28d: int | None


class KeywordRecord(EntityModel):
    id: str
    keyword: str
    volume: int | None
    difficulty: int | None
    cpc: float | None
    intent: str | None
    facts_fetched_at: JsDateTime | None
    first_source: str
    seed_keyword_id: str | None
    cluster_id: str | None
    branded: bool
    our_position: int | None
    our_url: str | None
    impressions_28d: int
    clicks_28d: int
    impressions_prev_28d: int
    clicks_prev_28d: int
    impressions_ly_28d: int | None
    clicks_ly_28d: int | None
    created_at: JsDateTime


class KeywordFilter(EntityModel):
    source: str | None = None
    cluster_id: str | None = None
    branded: bool | None = None
    search: str | None = None
    has_facts: bool | None = None


class KeywordGscPageRecord(EntityModel):
    id: str
    keyword_id: str
    page_id: str
    position: float | None
    impressions_28d: int
    clicks_28d: int
    impressions_prev_28d: int
    clicks_prev_28d: int
    impressions_ly_28d: int | None
    clicks_ly_28d: int | None
    ctr: float | None
    ctr_gap: float | None
    leader_days_90d: int
    coverage: float | None
    lexical_hit: bool


class KeywordContentPageRecord(EntityModel):
    id: str
    keyword_id: str
    page_id: str
    coverage: float
    lexical_hit: bool


class ClusterRecord(EntityModel):
    id: str
    head_keyword_id: str
    size: int
    volume_sum: int
    difficulty_median: float | None
    owner_page_id: str | None
    owner_coverage: float | None
    site_similarity: float | None
    rebuilt_at: JsDateTime | None


class CompetitorRecord(EntityModel):
    id: str
    domain: str
    brand_terms: list[str]
    first_source: str
    intersections: int | None
    avg_position: float | None
    state: str
    fetched_at: JsDateTime | None


class CompetitorUpdateRequest(RequestModel):
    state: str | None = None
    brand_terms: list[str] | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str | None:
        return None if value is None else fields.competitor_state(value)

    @field_validator("brand_terms", mode="before")
    @classmethod
    def _brand_terms(cls, value: Any) -> list[str] | None:
        return None if value is None else fields.brand_terms(value)


class PageSuggestionRecord(EntityModel):
    id: str
    job_id: str
    action: str
    page_id: str | None
    topic_key: str
    cluster_id: str | None
    pair_id: str | None
    merge_into_page_id: str | None
    strategies: list[str]
    suggestion: str
    evidence: dict[str, Any]
    coverage_at_creation: float | None
    impressions_at_creation: int | None
    target_position: float | None
    state: str
    search_score: float | None
    confidence: float | None
    score: float | None
    verified_at: JsDateTime | None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageSuggestionFilter(EntityModel):
    state: str | None = None
    action: str | None = None
    job_id: str | None = None
    page_id: str | None = None
    topic_key: str | None = None


class PageSuggestionSummary(EntityModel):
    add: dict[str, int] = {}
    edit: dict[str, int] = {}
    delete: dict[str, int] = {}


class RollupResult(EntityModel):
    pages: int = 0
    keywords: int = 0
    keyword_pages: int = 0
    embedded: int = 0
    rollup_at: datetime | None = None


class ReconcileResult(EntityModel):
    done: int = 0
    stale: int = 0
    pending_precompute: bool = False


class OverviewResponse(EntityModel):
    keywords: int
    keywords_with_facts: int
    clusters: int
    competitors_confirmed: int
    suggestions: PageSuggestionSummary
    state: SiteStateRecord


class NewPageSuggestion(EntityModel):
    action: str
    topic_key: str
    page_id: str | None = None
    cluster_id: str | None = None
    merge_into_page_id: str | None = None
    keyword_ids: list[str] = Field(default_factory=list)
    strategy: str
    suggestion: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    search_score: float | None = None
    target_position: float | None = None
    state: str = "draft"
    pair_with: int | None = None


class Collision(EntityModel):
    id: str
    state: str
    strategies: list[str]


class CreateResult(EntityModel):
    drafts: int = 0
    ids: list[str] = Field(default_factory=list)
    collided: list[Collision] = Field(default_factory=list)
    filtered: dict[str, int] = Field(default_factory=dict)


class SavePageSuggestionRequest(RequestModel):
    job_id: str
    action: str = Field(default="", validate_default=True)
    topic_key: str = Field(default="", validate_default=True)
    page_id: str | None = None
    merge_into_page_id: str | None = None
    keyword_ids: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)
    suggestion: str = Field(default="", validate_default=True)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action", mode="before")
    @classmethod
    def _action(cls, value: Any) -> str:
        return fields.action(value)

    @field_validator("topic_key", mode="before")
    @classmethod
    def _topic_key(cls, value: Any) -> str:
        cleaned = fields.keyword(value)
        if not cleaned:
            raise ValueError("A suggestion needs a topic key.")
        return cleaned

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return fields.suggestion(value)

    @field_validator("terms", mode="before")
    @classmethod
    def _terms(cls, value: Any) -> list[str]:
        return fields.keywords(value)


class ScreenResult(EntityModel):
    screened: int = 0
    passed: int = 0
    llm_rejected: int = 0
    failed: int = 0
    stopped: str | None = None


class ReviewResult(EntityModel):
    reviewed: int = 0
    llm_rejected: int = 0
    failed: int = 0
    needs_serp: list[str] = Field(default_factory=list)
    stopped: str | None = None


class RankResult(EntityModel):
    kept: int = 0
    llm_rejected: int = 0


class PageEditsRequest(RequestModel):
    job_id: str
    evidence: str = "all"
    page_ids: list[str] | None = None
    keyword_ids: list[str] | None = None
    min_position: float = 4
    max_position: float = 20
    min_impressions: int = 100
    min_questions: int = 3
    min_drop: float = 0.3

    @field_validator("evidence", mode="before")
    @classmethod
    def _evidence(cls, value: Any) -> str:
        chosen = str(value or "all")
        allowed = ("all", "gsc", "cluster", "ctr", "questions", "decay")
        if chosen not in allowed:
            raise ValueError(f'Invalid evidence "{chosen}". Allowed values: {", ".join(allowed)}.')
        return chosen


class CannibalisationRequest(RequestModel):
    job_id: str
    page_ids: list[str] | None = None
    min_shared_impressions: int = 50


class ScreenRequest(RequestModel):
    job_id: str
    ids: list[str] | None = None
    question: str | None = None
    limit: int = 200


class ReviewRequest(RequestModel):
    job_id: str
    prompt: str = Field(default="", validate_default=True)
    ids: list[str] | None = None
    limit: int = 200

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class RankRequest(RequestModel):
    job_id: str
    budget_add: int = 10
    budget_edit: int = 20
    budget_delete: int = 5


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


class GapPagesRequest(RequestModel):
    job_id: str
    keyword_ids: list[str] | None = None
    min_volume: int = 50
    max_difficulty: int = 60


class TopicPagesRequest(RequestModel):
    job_id: str
    topic: str = Field(default="", validate_default=True)
    source_table: str | None = None
    ideas_per_seed: int = 30
    dry_run: bool = False

    @field_validator("topic", mode="before")
    @classmethod
    def _topic(cls, value: Any) -> str:
        cleaned = fields.keyword(value)
        if not cleaned:
            raise ValueError("A topic is needed.")
        return cleaned


class TopicPagesResult(EntityModel):
    suggestions: CreateResult
    collected: dict[str, Any]
