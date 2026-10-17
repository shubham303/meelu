from pydantic import BaseModel, Field, field_validator

from src.core.schemas import EntityModel, RequestModel
from src.seo.keyword_clusters.schemas import normalize_keyword
from src.seo.serp_results.constants import Verdict


class SerpResultsRequest(RequestModel):
    keyword: str = Field(min_length=1)
    use_cache: bool = False
    location_code: int | None = None

    @field_validator("keyword")
    @classmethod
    def _keyword(cls, value: str) -> str:
        cleaned = normalize_keyword(value)
        if not cleaned:
            raise ValueError("Pass a keyword.")
        return cleaned


class SerpResult(EntityModel):
    position: int
    url: str
    domain: str
    title: str | None = None
    description: str | None = None
    breadcrumb: str | None = None
    website_name: str | None = None
    highlighted: list[str] = Field(default_factory=list)
    date: str | None = None
    rating: float | None = None
    rating_votes: int | None = None
    price: str | None = None
    featured_snippet: bool = False
    video: bool = False
    page_rank: int | None = None
    domain_rank: int | None = None
    weak: bool
    ours: bool


class SiblingCheck(EntityModel):
    keyword: str
    shared_domains: int
    overlap: float


class SerpPull(BaseModel):
    keyword: str
    market: dict
    serp: dict | None
    main: list[dict]
    siblings: list[SiblingCheck]


class SerpResults(EntityModel):
    keyword: str
    location_code: int
    language_code: str
    checked_at: str | None = None
    results: list[SerpResult]
    weak_top: int
    siblings: list[SiblingCheck]
    sibling_overlap: float | None = None
    verdict: Verdict
    reasons: list[str]
    message: str | None = None
