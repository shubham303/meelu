from pydantic import Field, field_validator

from src.core.schemas import EntityModel, RequestModel
from src.providers.seo_data.shape import own_domain
from src.seo.site_seo.constants import MAX_ITEMS_PER_CALL, SeoList


def clean_domains(values: list[str]) -> list[str]:
    cleaned = [d for d in dict.fromkeys(own_domain(v) for v in values) if d]
    if not cleaned:
        raise ValueError("Pass at least one domain.")
    return cleaned


class CompetitorRecord(EntityModel):
    id: str
    domain: str


class SiteSeoRecord(EntityModel):
    site_id: str
    competitors: list[str]
    backlink_opportunities: list[str]


class SeoListItemsRequest(RequestModel):
    items: list[str] = Field(min_length=1, max_length=MAX_ITEMS_PER_CALL)

    @field_validator("items")
    @classmethod
    def _items(cls, value: list[str]) -> list[str]:
        return clean_domains(value)


class SeoListChange(EntityModel):
    list: SeoList
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    unchanged: list[str] = Field(default_factory=list)
    items: list[str]


class FoundCompetitor(EntityModel):
    domain: str
    sources: list[str]
    shared_keywords: int | None = None
    avg_position: float | None = None
    visibility: float | None = None
    saved: bool = False


class FoundCompetitors(EntityModel):
    sampled_queries: int
    competitors: list[FoundCompetitor]


class BacklinkOpportunity(EntityModel):
    domain: str
    links_to: list[str]
    rank: int | None = None
    backlinks_to_competitors: int = 0
    spam_score: int | None = None
    saved: bool = False


class BacklinkOpportunities(EntityModel):
    competitors: list[str]
    total: int
    opportunities: list[BacklinkOpportunity]
