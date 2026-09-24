from typing import Literal

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.pagination import PaginationParams
from src.site_pages import service
from src.site_pages.schemas import (
    MISSING_FIELDS,
    STATUS_CLASSES,
    VIEWS,
    SitePageFilters,
    SitePageListResult,
)
from src.site_pages.stage import STAGES


@tool(desk="pages")
async def search_page(
    search_text: str,
    url: str | None = None,
    urls: list[str] | None = None,
    ids: list[str] | None = None,
    page_type: str | None = None,
    page_types: list[str] | None = None,
    needs_audit: bool | None = None,
    status: Literal[STATUS_CLASSES] | None = None,
    status_codes: list[int] | None = None,
    stage: Literal[STAGES] | None = None,
    sort: str | None = None,
    url_contains: str | None = None,
    title: str | None = None,
    title_contains: str | None = None,
    meta_contains: str | None = None,
    text_contains: str | None = None,
    lang: str | None = None,
    format: str | None = None,
    embed_state: str | None = None,
    in_sitemap: bool | None = None,
    orphan: bool | None = None,
    shallow: bool | None = None,
    blocked_by_robots: bool | None = None,
    noindex: bool | None = None,
    canonical_elsewhere: bool | None = None,
    redirects: bool | None = None,
    missing: list[Literal[MISSING_FIELDS]] | None = None,
    min_words: int | None = None,
    max_words: int | None = None,
    min_depth: int | None = None,
    max_depth: int | None = None,
    min_inlinks: int | None = None,
    max_inlinks: int | None = None,
    crawled_before: str | None = None,
    crawled_after: str | None = None,
    changed_before: str | None = None,
    changed_after: str | None = None,
    published_before: str | None = None,
    published_after: str | None = None,
    view: Literal[VIEWS] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> SitePageListResult:
    """Hybrid search over the crawled page corpus: search_text is matched against
    page passages by keyword and by meaning, reranked, and returned with the
    matching snippet. Plain crawl-fact filters are cheaper as SQL over site_pages."""
    filters = SitePageFilters(
        url=url,
        urls=urls,
        ids=ids,
        page_type=page_type,
        page_types=page_types,
        needs_audit=needs_audit,
        status=status,
        status_code=status_codes,
        stage=stage,
        sort=sort,
        url_contains=url_contains,
        title=title,
        title_contains=title_contains,
        meta_contains=meta_contains,
        text_contains=text_contains,
        lang=lang,
        format=format,
        embed_state=embed_state,
        in_sitemap=in_sitemap,
        orphan=orphan,
        shallow=shallow,
        blocked_by_robots=blocked_by_robots,
        noindex=noindex,
        canonical_elsewhere=canonical_elsewhere,
        redirects=redirects,
        missing=missing,
        min_words=min_words,
        max_words=max_words,
        min_depth=min_depth,
        max_depth=max_depth,
        min_inlinks=min_inlinks,
        max_inlinks=max_inlinks,
        crawled_before=crawled_before,
        crawled_after=crawled_after,
        changed_before=changed_before,
        changed_after=changed_after,
        published_before=published_before,
        published_after=published_after,
    )
    paging = PaginationParams(page=page, page_size=page_size).validate()
    ctx = require_site()
    async with unit_of_work() as db:
        return await service.pages(db, ctx.site_id, filters, paging, view, search_text)
