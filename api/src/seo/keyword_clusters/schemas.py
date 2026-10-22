from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.keyword_clusters.constants import (
    DEFAULT_COMPETITOR_CLUSTERS,
    DEFAULT_IMPRESSIONS_LOOKBACK,
    DEFAULT_SEARCH_CONSOLE_QUERIES,
    MAX_COMPETITOR_CLUSTERS,
    MAX_DELETE,
    MAX_IMPRESSIONS_LOOKBACK,
    MAX_KEYWORDS_TO_ADD,
    MAX_SEARCH_CONSOLE_QUERIES,
    MAX_SEEDS,
    NO_CLUSTER_GIVEN,
    TOO_MANY_TO_DELETE,
    Importance,
    SearchIntent,
)
from src.seo.market import country_of


def normalize_keyword(raw: Any) -> str:
    return " ".join(str(raw or "").lower().split())


class SeedClustersRequest(RequestModel):
    seeds: list[str] = Field(min_length=1)
    min_volume: int | None = Field(default=None, ge=0)

    @field_validator("seeds")
    @classmethod
    def _seeds(cls, value: list[str]) -> list[str]:
        cleaned = [s for s in dict.fromkeys(normalize_keyword(v) for v in value) if s]
        if not cleaned:
            raise ValueError("Pass at least one seed keyword.")
        if len(cleaned) > MAX_SEEDS:
            raise ValueError(f"At most {MAX_SEEDS} seed keywords per call.")
        return cleaned


class KeywordsClusterRequest(RequestModel):
    keywords: list[str] = Field(min_length=1)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        cleaned = [k for k in dict.fromkeys(normalize_keyword(v) for v in value) if k]
        if not cleaned:
            raise ValueError("Pass at least one keyword.")
        if len(cleaned) > MAX_KEYWORDS_TO_ADD:
            raise ValueError(f"At most {MAX_KEYWORDS_TO_ADD} keywords per call.")
        return cleaned


class SearchConsoleClustersRequest(RequestModel):
    limit: int = Field(default=DEFAULT_SEARCH_CONSOLE_QUERIES, ge=1, le=MAX_SEARCH_CONSOLE_QUERIES)
    min_volume: int | None = Field(default=None, ge=0)


class CompetitorClustersRequest(RequestModel):
    limit: int = Field(default=DEFAULT_COMPETITOR_CLUSTERS, ge=1, le=MAX_COMPETITOR_CLUSTERS)
    min_volume: int | None = Field(default=None, ge=0)
    lookback: int = Field(default=DEFAULT_IMPRESSIONS_LOOKBACK, ge=1, le=MAX_IMPRESSIONS_LOOKBACK)


class KeywordFacts(BaseModel):
    keyword: str
    ads_volume: int | None = None
    clickstream_volume: int | None = None
    core_keyword: str | None = None


class KeywordLabels(BaseModel):
    intent: SearchIntent | None = None
    importance: Importance | None = None
    is_brand_keyword: bool | None = None


class ClusterDraft(BaseModel):
    main_keyword: str
    keywords: list[str]
    core_keyword: str | None
    seeds: list[str]
    location_code: int
    language_code: str
    volume: int
    intent: SearchIntent | None = None
    importance: Importance | None = None
    is_brand_keyword: bool | None = None


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
    intent: SearchIntent | None = None
    importance: Importance | None = None
    is_brand_keyword: bool | None = None
    is_ranked: bool
    created_at: JsDateTime
    updated_at: JsDateTime

    @computed_field
    @property
    def country(self) -> str | None:
        return country_of(self.location_code)


class ClusterDeleted(EntityModel):
    id: str
    main_keyword: str
    keywords: list[str]


class ClustersDeleteRequest(RequestModel):
    cluster_ids: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    @field_validator("cluster_ids")
    @classmethod
    def _cluster_ids(cls, value: list[str]) -> list[str]:
        return [i for i in dict.fromkeys(v.strip() for v in value) if i]

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        return [k for k in dict.fromkeys(normalize_keyword(v) for v in value) if k]

    @model_validator(mode="after")
    def _something(self) -> ClustersDeleteRequest:
        if not self.cluster_ids and not self.keywords:
            raise ValueError(NO_CLUSTER_GIVEN)
        if len(self.cluster_ids) + len(self.keywords) > MAX_DELETE:
            raise ValueError(TOO_MANY_TO_DELETE)
        return self


class ClustersDeleted(EntityModel):
    deleted: list[ClusterDeleted]
    missing_ids: list[str]
    unclustered_keywords: list[str]


class ClusterFilters(RequestModel):
    search: str | None = None
    min_volume: int | None = None
    ranked: bool | None = None
