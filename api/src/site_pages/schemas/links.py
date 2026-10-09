from collections.abc import Iterable
from typing import Any

from pydantic import field_validator

from src.core.schemas import EntityModel, RequestModel
from src.site_pages.url import normalise_url

LINK_REGIONS = ("body", "nav", "header", "footer", "aside", "breadcrumb", "pagination")


class PageLinkInput(RequestModel):
    url: str
    anchor: str | None = None
    rel: str | None = None
    region: str = "body"
    count: int = 1


class PageLink(EntityModel):
    url: str
    region: str
    rel: str | None = None
    anchor: str | None = None
    count: int
    followable: bool


def _region(region: str | None) -> str:
    wanted = (region or "").strip().lower()
    return wanted if wanted in LINK_REGIONS else "body"


def _followable(rel: str | None) -> bool:
    return "nofollow" not in (rel or "").lower()


def merge_links(links: Iterable[PageLinkInput]) -> list[PageLink]:
    merged: dict[tuple[str, str], PageLink] = {}
    for link in links:
        url = normalise_url(link.url)
        if url == "":
            continue
        region = _region(link.region)
        count = max(link.count, 1)
        found = merged.get((url, region))
        if found is None:
            merged[(url, region)] = PageLink(
                url=url,
                region=region,
                rel=link.rel,
                anchor=link.anchor,
                count=count,
                followable=_followable(link.rel),
            )
            continue
        found.count += count
        found.followable = found.followable or _followable(link.rel)
        if found.anchor is None:
            found.anchor = link.anchor
    return list(merged.values())


def stored_links(value: Any) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    parsed = [v if isinstance(v, PageLinkInput) else PageLinkInput.model_validate(v) for v in value]
    return [link.model_dump() for link in merge_links(parsed)]


class SitePageOutlinksItem(RequestModel):
    url: str
    links: list[PageLinkInput]

    @field_validator("url", mode="before")
    @classmethod
    def _normalise_url(cls, v: Any) -> Any:
        return normalise_url(v) if isinstance(v, str) else v


class SitePageOutlinksRequest(RequestModel):
    pages: list[SitePageOutlinksItem]


class SitePageOutlinksResult(EntityModel):
    pages: int
    links: int
    unresolved: list[str]


class NewSitePageLink(EntityModel):
    dst_page_id: str
    dst_url: str
    region: str
    rel: str | None = None
    anchor: str | None = None
    count: int
    followable: bool
    dst_canonical: bool
