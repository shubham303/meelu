from datetime import datetime
from typing import Any, Literal

import pycountry
from pydantic import Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.sites.host import read_host

SiteSort = Literal["created", "name", "domain", "crawled"]
SiteStatus = Literal["active", "disabled"]

AGENT_WRITABLE = (
    "summary",
    "socialLinks",
    "markets",
    "language",
    "name",
    "domain",
    "repoUrl",
    "sitemapUrls",
)


def _host(value: Any) -> str:
    host = read_host(value)
    if not host:
        raise ValueError(
            f'"{value}" doesn\'t look like a website — give the host it actually serves on, '
            f'such as "www.example.com" or "example.com". The two are separate websites '
            f"unless one redirects to the other, so enter the one you mean."
        )
    return host


def _url_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array of URLs.")
    return [u for u in (str(v) for v in value) if u.strip() != ""]


def country_codes(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("markets must be an array of two-letter country codes.")
    codes = [str(v).strip().upper() for v in value if str(v or "").strip()]
    codes = ["GB" if c == "UK" else c for c in codes]
    unknown = [c for c in codes if pycountry.countries.get(alpha_2=c) is None]
    if unknown:
        raise ValueError(f"{', '.join(unknown)} is not a two-letter country code such as US or GB.")
    return list(dict.fromkeys(codes))


def language_code(value: Any) -> str | None:
    code = str(value or "").strip().lower()
    if not code:
        return None
    if len(code) != 2 or pycountry.languages.get(alpha_2=code) is None:
        raise ValueError(f'"{value}" is not a two-letter language code such as en or de.')
    return code


def _social_links(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("socialLinks must be an array.")
    for link in value:
        if (
            not isinstance(link, dict)
            or not isinstance(link.get("platform"), str)
            or not link["platform"].strip()
        ):
            raise ValueError("Every socialLinks entry needs a platform.")
        if not isinstance(link.get("url"), str) or not link["url"].strip():
            raise ValueError("Every socialLinks entry needs a url.")
    return value


class SiteFilters(RequestModel):
    q: str | None = None
    domain: str | None = None
    status: SiteStatus | None = None
    has_repo: bool | None = None
    never_crawled: bool | None = None
    crawled_before: datetime | None = None
    crawled_after: datetime | None = None
    sort: SiteSort | None = None

    @field_validator("domain", mode="before")
    @classmethod
    def _validate_domain(cls, v: Any) -> str | None:
        return None if v in (None, "") else _host(v)


class SiteCreateRequest(RequestModel):
    domain: str
    name: str
    markets: list[str] = Field(default_factory=list)
    language: str | None = None
    repo_url: str | None = None
    summary: str | None = None
    social_links: list[dict[str, Any]] = Field(default_factory=list)
    sitemap_urls: list[str] = Field(default_factory=list)
    gsc_property: str | None = None
    ga_property: str | None = None

    @field_validator("domain", mode="before")
    @classmethod
    def _validate_domain(cls, v: Any) -> str:
        return _host(v)

    @field_validator("social_links", mode="before")
    @classmethod
    def _validate_social_links(cls, v: Any) -> list[dict[str, Any]]:
        return _social_links(v)

    @field_validator("sitemap_urls", mode="before")
    @classmethod
    def _validate_sitemap_urls(cls, v: Any) -> list[str]:
        return _url_list(v, "sitemapUrls")

    @field_validator("markets", mode="before")
    @classmethod
    def _validate_markets(cls, v: Any) -> list[str]:
        return country_codes(v)

    @field_validator("language", mode="before")
    @classmethod
    def _validate_language(cls, v: Any) -> str | None:
        return language_code(v)


class SiteUpdateRequest(RequestModel):
    domain: str | None = None
    name: str | None = None
    markets: list[str] | None = None
    language: str | None = None
    repo_url: str | None = None
    summary: str | None = None
    social_links: list[dict[str, Any]] | None = None
    sitemap_urls: list[str] | None = None
    sitemap_url_count: int | None = None
    sitemap_at_root: bool | None = None
    robots_txt: str | None = None
    robots_status: int | None = None
    robots_fetched_at: datetime | None = None
    llms_txt: str | None = None
    llms_status: int | None = None
    llms_fetched_at: datetime | None = None
    crawler_access: Any | None = None
    host_variants: Any | None = None
    last_crawled_at: datetime | None = None
    gsc_property: str | None = None
    ga_property: str | None = None

    @field_validator("domain", mode="before")
    @classmethod
    def _validate_domain(cls, v: Any) -> str | None:
        return None if v is None else _host(v)

    @field_validator("social_links", mode="before")
    @classmethod
    def _validate_social_links(cls, v: Any) -> list[dict[str, Any]] | None:
        return None if v is None else _social_links(v)

    @field_validator("sitemap_urls", mode="before")
    @classmethod
    def _validate_sitemap_urls(cls, v: Any) -> list[str] | None:
        return None if v is None else _url_list(v, "sitemapUrls")

    @field_validator("markets", mode="before")
    @classmethod
    def _validate_markets(cls, v: Any) -> list[str] | None:
        return None if v is None else country_codes(v)

    @field_validator("language", mode="before")
    @classmethod
    def _validate_language(cls, v: Any) -> str | None:
        return language_code(v)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class SiteAgentUpdateRequest(SiteUpdateRequest):
    @model_validator(mode="before")
    @classmethod
    def _only_agent_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        rejected = [k for k in data if k not in AGENT_WRITABLE]
        if rejected:
            raise ValueError(
                f"{', '.join(rejected)} is not part of the website record. "
                f"This endpoint accepts {', '.join(AGENT_WRITABLE)}."
            )
        return data


class SiteRef(EntityModel):
    id: str
    user_id: str
    domain: str
    status: str


class SiteRecord(EntityModel):
    id: str
    user_id: str
    domain: str
    name: str
    status: SiteStatus
    markets: list[str]
    language: str | None = None
    repo_url: str | None = None
    summary: str | None = None
    social_links: list[Any]
    sitemap_urls: list[str]
    sitemap_url_count: int | None = None
    sitemap_at_root: bool | None = None
    robots_txt: str | None = None
    robots_status: int | None = None
    robots_fetched_at: JsDateTime | None = None
    llms_txt: str | None = None
    llms_status: int | None = None
    llms_fetched_at: JsDateTime | None = None
    crawler_access: Any | None = None
    host_variants: Any | None = None
    last_crawled_at: JsDateTime | None = None
    gsc_property: str | None = None
    ga_property: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class SiteResponse(EntityModel):
    id: str
    domain: str
    name: str
    status: SiteStatus
    markets: list[str]
    language: str | None = None
    repo_url: str | None = None
    summary: str | None = None
    social_links: list[Any]
    sitemap_urls: list[str]
    sitemap_url_count: int | None = None
    sitemap_at_root: bool | None = None
    robots_txt: str | None = None
    robots_status: int | None = None
    robots_fetched_at: JsDateTime | None = None
    llms_txt: str | None = None
    llms_status: int | None = None
    llms_fetched_at: JsDateTime | None = None
    crawler_access: Any | None = None
    host_variants: Any | None = None
    last_crawled_at: JsDateTime | None = None
    gsc_property: str | None = None
    ga_property: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class SiteListItemResponse(EntityModel):
    id: str
    domain: str
    name: str
    status: SiteStatus
    markets: list[str]
    language: str | None = None
    repo_url: str | None = None
    summary: str | None = None
    last_crawled_at: JsDateTime | None = None
    gsc_property: str | None = None
    ga_property: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class SiteDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)
