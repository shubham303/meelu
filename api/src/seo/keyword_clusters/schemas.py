from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.keyword_clusters.constants import (
    DEFAULT_SOURCE_KEYWORDS,
    MAX_SEEDS,
    MAX_SOURCE_KEYWORDS,
    ClusterSource,
)
from src.seo.market import country_of


def normalize_keyword(raw: Any) -> str:
    return " ".join(str(raw or "").lower().split())


class CreateClustersRequest(RequestModel):
    source: ClusterSource = "seeds"
    seeds: list[str] = Field(default_factory=list)
    limit: int = Field(default=DEFAULT_SOURCE_KEYWORDS, ge=1, le=MAX_SOURCE_KEYWORDS)
    min_volume: int | None = Field(default=None, ge=0)

    @field_validator("seeds")
    @classmethod
    def _seeds(cls, value: list[str]) -> list[str]:
        cleaned = [s for s in dict.fromkeys(normalize_keyword(v) for v in value) if s]
        if len(cleaned) > MAX_SEEDS:
            raise ValueError(f"At most {MAX_SEEDS} seed keywords per call.")
        return cleaned

    @model_validator(mode="after")
    def _seeds_for_seed_source(self) -> "CreateClustersRequest":
        if self.source == "seeds" and not self.seeds:
            raise ValueError("Pass at least one seed keyword.")
        return self


class KeywordFacts(BaseModel):
    keyword: str
    ads_volume: int | None = None
    clickstream_volume: int | None = None
    core_keyword: str | None = None


class ClusterDraft(BaseModel):
    main_keyword: str
    keywords: list[str]
    core_keyword: str | None
    seeds: list[str]
    location_code: int
    language_code: str
    volume: int


class Competitor(BaseModel):
    position: int
    url: str
    domain: str
    title: str | None = None
    page_rank: int | None = None
    domain_rank: int | None = None
    strength: float
    smoothed_strength: float
    intent_fit: float
    pass_chance: float


class ClusterMetrics(BaseModel):
    winnability: float
    p_top_three: float
    p_page_one: float
    likely_position: int
    our_position: int | None
    our_url: str | None
    our_strength: float
    intent_fit: float | None
    climb: list[dict[str, Any]]


class ClusterRecord(EntityModel):
    id: str
    site_id: str
    main_keyword: str
    keywords: list[str]
    core_keyword: str | None = None
    seeds: list[str]
    location_code: int
    language_code: str
    volume: int
    winnability: float | None = None
    p_top_three: float | None = None
    p_page_one: float | None = None
    likely_position: int | None = None
    our_position: int | None = None
    our_url: str | None = None
    our_strength: float | None = None
    intent_fit: float | None = None
    is_ranked: bool
    competitors: list[str] = Field(default_factory=list)
    climb: list[Any]
    metrics_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime

    @computed_field
    @property
    def country(self) -> str | None:
        return country_of(self.location_code)


class ClusterBrief(EntityModel):
    id: str
    main_keyword: str
    size: int
    volume: int
    winnability: float | None = None


class ClustersCreated(EntityModel):
    source: ClusterSource
    candidates: int
    already_clustered: int
    noise: int
    irrelevant: int
    clusters: int
    top: list[ClusterBrief]


class MetricsComputed(EntityModel):
    computed: int
    failed: list[str]
    clusters: list[ClusterBrief]


class ClusterFilters(RequestModel):
    search: str | None = None
    min_volume: int | None = None
    scored: bool | None = None
    ranked: bool | None = None
