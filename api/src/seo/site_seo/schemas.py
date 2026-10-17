from datetime import datetime

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.providers.seo_data.shape import own_domain
from src.seo.site_seo.constants import MAX_DOMAINS_PER_CALL


def clean_domains(values: list[str]) -> list[str]:
    cleaned = [d for d in dict.fromkeys(own_domain(v) for v in values) if d]
    if not cleaned:
        raise ValueError("Pass at least one domain.")
    return cleaned


class CompetitorRecord(EntityModel):
    id: str
    domain: str
    domain_rank: int | None = None
    backlinks_fetched_at: JsDateTime | None = None
    created_at: JsDateTime


class Competitor(CompetitorRecord):
    backlinks: int = 0


class DomainsRequest(RequestModel):
    domains: list[str] = Field(min_length=1, max_length=MAX_DOMAINS_PER_CALL)

    @field_validator("domains")
    @classmethod
    def _domains(cls, value: list[str]) -> list[str]:
        return clean_domains(value)


class CompetitorsChange(EntityModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    unchanged: list[str] = Field(default_factory=list)
    competitors: list[str]


class BacklinksOfDomain(EntityModel):
    domain: str
    backlinks: int


class BacklinksFetched(EntityModel):
    fetched: list[BacklinksOfDomain]
    not_saved: list[str] = Field(default_factory=list)


class BacklinkDraft(EntityModel):
    site_domain: str
    backlink_url: str
    backlinking_domain: str
    backlinking_url: str
    anchor: str | None = None
    item_type: str | None = None
    dofollow: bool | None = None
    link_attributes: list[str] = Field(default_factory=list)
    semantic_location: str | None = None
    links_from_domain: int | None = None
    is_lost: bool | None = None
    is_broken: bool | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    backlink_spam_score: int | None = None
    domain_spam_score: int | None = None
    domain_rank: int | None = None
    page_rank: int | None = None
    is_ip: bool | None = None
    platform_type: list[str] = Field(default_factory=list)
    country: str | None = None
    page_title: str | None = None
    page_language: str | None = None
    page_status_code: int | None = None
    page_external_links: int | None = None
    dismissed: bool = False


class BacklinkOpportunity(EntityModel):
    domain: str
    links_to: list[str]
    domain_rank: int | None = None
    domain_spam_score: int | None = None
    backlink_spam_score: int | None = None
    dofollow: bool
    example_url: str
    example_anchor: str | None = None


class BacklinkDomainRemoved(EntityModel):
    domain: str
    backlinks_removed: int


class BacklinkDomainRequest(RequestModel):
    domain: str

    @field_validator("domain")
    @classmethod
    def _domain(cls, value: str) -> str:
        return clean_domains([value])[0]


class OpportunitiesDismissed(EntityModel):
    dismissed: list[str]
    not_found: list[str] = Field(default_factory=list)
