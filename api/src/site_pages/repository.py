from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Integer,
    and_,
    bindparam,
    case,
    cast,
    delete,
    func,
    literal,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginationParams, PaginationService
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_search.models.site_page_index_status import SitePageIndexStatus
from src.site_pages.models.site_page_link import SitePageLink
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.schemas import (
    PageLinkInput,
    ChunkCounts,
    CrawlCountsResult,
    CrawlKnownPageRecord,
    DepthCount,
    DiscoveryPage,
    PageTypeCount,
    ShallowReasonCount,
    SiteChunkRecord,
    SitemapPresenceResult,
    SitePageCrawlItem,
    SitePageDiscoveryRecord,
    SitePageEdge,
    SitePageExportRecord,
    SitePageFilters,
    SitePageLandingSeed,
    SitePageLinkRecord,
    SitePageLinksResult,
    SitePageListResult,
    SitePageRecord,
    SitePageRef,
    SitePageSlimRecord,
    SitePageStatsRecord,
    SitePageTextRecord,
    StageCount,
)
from src.site_pages.stage import CRAWL_COMPLETE_SQL, STAGE_SQL
from src.site_pages.url import normalise_url

NEEDS_AUDIT = and_(SitePage.status == 200, SitePage.content_hash.is_not(None))

PAGE_TYPE = (
    select(SitePageLlmExtraction.page_type)
    .where(SitePageLlmExtraction.page_id == SitePage.id)
    .correlate(SitePage)
    .scalar_subquery()
    .label("page_type")
)

SLIM = (
    SitePage.id,
    SitePage.site_id,
    SitePage.chunked_from_hash,
    SitePage.url,
    SitePage.title,
    PAGE_TYPE,
    SitePage.status,
    SitePage.inlinks,
    SitePage.link_score,
    SitePage.content_hash,
    SitePage.shallow,
    SitePage.shallow_reason,
    SitePage.blocked_by_robots,
    SitePage.last_crawled_at,
    SitePage.embed_state,
    SitePage.depth,
    SitePage.word_count,
    SitePage.content_changed_at,
    SitePage.in_sitemap,
    SitePage.fetch_error,
    SitePage.redirect_to,
)

TEXT_VIEW = (
    SitePage.id,
    SitePage.url,
    SitePage.title,
    SitePage.status,
    SitePage.shallow,
    SitePage.blocked_by_robots,
    SitePage.content_hash,
    SitePage.chunked_from_hash,
    SitePage.word_count,
    SitePage.body_text,
)


def _link_count(external: bool):
    return (
        select(cast(func.count(), Integer))
        .select_from(SitePageLink)
        .where(
            SitePageLink.src_page_id == SitePage.id,
            SitePageLink.external.is_(external),
        )
        .correlate(SitePage)
        .scalar_subquery()
    )


OUT_LINK_COUNT = _link_count(False)
EXTERNAL_LINK_COUNT = _link_count(True)

IMAGE_BYTES_SQL = text(
    """(select coalesce(sum((im->>'bytes')::bigint), 0)
    from jsonb_array_elements(site_pages.images) im where im->>'bytes' is not null)::int"""
).columns(image_bytes=Integer)

EXPORT = (
    SitePage.url,
    SitePage.status,
    PAGE_TYPE,
    SitePage.format,
    SitePage.title,
    SitePage.title_pixels,
    SitePage.meta_description,
    SitePage.h1,
    SitePage.lang,
    SitePage.schema_types,
    SitePage.canonical,
    SitePage.robots_directives,
    SitePage.x_robots_tag,
    SitePage.blocked_by_robots,
    SitePage.viewport_meta,
    SitePage.nosnippet_count,
    SitePage.social_meta_count,
    SitePage.has_google_analytics,
    SitePage.word_count,
    SitePage.inlinks,
    SitePage.depth,
    SitePage.in_sitemap,
    SitePage.shallow,
    SitePage.shallow_reason,
    SitePage.redirect_to,
    SitePage.redirect_hops,
    SitePage.fetch_error,
    SitePage.content_type,
    SitePage.published_at,
    SitePage.modified_at,
    SitePage.content_changed_at,
    SitePage.last_crawled_at,
    SitePage.embed_state,
    SitePage.content_hash,
    SitePage.chunked_from_hash,
    SitePage.body_text.is_not(None).label("has_text"),
    OUT_LINK_COUNT.label("out_link_count"),
    EXTERNAL_LINK_COUNT.label("external_link_count"),
    cast(func.jsonb_array_length(SitePage.images), Integer).label("image_count"),
    IMAGE_BYTES_SQL.scalar_subquery().label("image_bytes"),
    cast(func.jsonb_array_length(SitePage.headings), Integer).label("heading_count"),
)


STATUS_SQL = {
    "ok": SitePage.status == 200,
    "error": or_(SitePage.status >= 400, SitePage.status == 0),
    "gone": SitePage.status.in_((404, 410)),
    "blocked": SitePage.status.in_((401, 403, 429)),
    "serverError": SitePage.status >= 500,
    "unreachable": SitePage.status == 0,
    "redirect": SitePage.status.between(300, 399),
}

STATUS_CLASSES = tuple(STATUS_SQL)

MISSING_SQL = {
    "title": or_(SitePage.title.is_(None), SitePage.title == ""),
    "metaDescription": or_(SitePage.meta_description.is_(None), SitePage.meta_description == ""),
    "h1": func.coalesce(func.array_length(SitePage.h1, 1), 0) == 0,
    "bodyText": or_(SitePage.body_text.is_(None), SitePage.body_text == ""),
}

MISSING_FIELDS = tuple(MISSING_SQL)

ORDER = {
    "url": (SitePage.url, "asc"),
    "inlinks": (SitePage.inlinks, "desc"),
    "score": (SitePage.link_score, "desc"),
    "depth": (func.coalesce(SitePage.depth, 0), "desc"),
    "words": (func.coalesce(SitePage.word_count, 0), "asc"),
    "status": (func.coalesce(SitePage.status, 0), "desc"),
    "crawled": (func.coalesce(SitePage.last_crawled_at, func.to_timestamp(0)), "asc"),
    "changed": (SitePage.content_changed_at, "asc"),
}

PAGE_SORTS = tuple(ORDER)


def _order_by(specs: list[tuple[str, str | None]] | None, match_ids: list[str] | None):
    if not specs:
        if match_ids:
            return [func.array_position(literal(list(match_ids), type_=ARRAY(TEXT)), SitePage.id)]
        specs = [("url", None)]
    keys = [s for s in specs if s[0] in ORDER]
    if not keys:
        keys = [("url", None)]
    order = []
    for key, direction in keys:
        expr, default = ORDER[key]
        chosen = direction if direction else default
        order.append(expr.asc().nulls_last() if chosen == "asc" else expr.desc().nulls_last())
    if not any(key == "url" for key, _ in keys):
        order.append(SitePage.url.asc())
    return order


def _conditions(site_id: str, f: SitePageFilters, match_ids: list[str] | None = None):
    where = [SitePage.site_id == site_id]
    if f.url:
        where.append(SitePage.url == f.url)
    if f.urls:
        where.append(SitePage.url.in_(f.urls))
    if f.ids:
        where.append(SitePage.id.in_(f.ids))
    if match_ids:
        where.append(SitePage.id.in_(match_ids))
    if f.page_type:
        where.append(PAGE_TYPE == f.page_type)
    if f.page_types:
        where.append(PAGE_TYPE.in_(f.page_types))
    if f.needs_audit:
        where.append(NEEDS_AUDIT)
    if f.stage:
        where.append(text(f"({STAGE_SQL[f.stage]})"))
    if f.status and f.status in STATUS_SQL:
        where.append(STATUS_SQL[f.status])
    if f.status_code:
        where.append(SitePage.status.in_(f.status_code))
    if f.url_contains:
        where.append(SitePage.url.ilike(f"%{f.url_contains}%"))
    if f.title:
        where.append(SitePage.title == f.title)
    if f.title_contains:
        where.append(SitePage.title.ilike(f"%{f.title_contains}%"))
    if f.meta_contains:
        where.append(SitePage.meta_description.ilike(f"%{f.meta_contains}%"))
    if f.text_contains:
        where.append(SitePage.body_text.ilike(f"%{f.text_contains}%"))
    if f.lang:
        where.append(SitePage.lang == f.lang)
    if f.format:
        where.append(SitePage.format == f.format)
    if f.embed_state:
        where.append(SitePage.embed_state == f.embed_state)
    if f.redirects is not None:
        where.append(
            SitePage.redirect_to.is_not(None) if f.redirects else SitePage.redirect_to.is_(None)
        )
    if f.in_sitemap is not None:
        where.append(SitePage.in_sitemap == f.in_sitemap)
    if f.orphan is not None:
        where.append(SitePage.inlinks == 0 if f.orphan else SitePage.inlinks > 0)
    if f.shallow is not None:
        where.append(SitePage.shallow == f.shallow)
    if f.blocked_by_robots is not None:
        where.append(SitePage.blocked_by_robots == f.blocked_by_robots)
    if f.noindex is not None:
        where.append(
            SitePage.robots_directives.ilike("%noindex%")
            if f.noindex
            else or_(
                SitePage.robots_directives.is_(None),
                SitePage.robots_directives.not_ilike("%noindex%"),
            )
        )
    if f.canonical_elsewhere is not None:
        where.append(
            and_(SitePage.canonical.is_not(None), SitePage.canonical != SitePage.url)
            if f.canonical_elsewhere
            else or_(SitePage.canonical.is_(None), SitePage.canonical == SitePage.url)
        )
    for missing_field in f.missing or []:
        where.append(MISSING_SQL[missing_field])
    if f.min_words is not None:
        where.append(SitePage.word_count >= f.min_words)
    if f.max_words is not None:
        where.append(SitePage.word_count <= f.max_words)
    if f.min_depth is not None:
        where.append(SitePage.depth >= f.min_depth)
    if f.max_depth is not None:
        where.append(SitePage.depth <= f.max_depth)
    if f.min_inlinks is not None:
        where.append(SitePage.inlinks >= f.min_inlinks)
    if f.max_inlinks is not None:
        where.append(SitePage.inlinks <= f.max_inlinks)
    if f.crawled_before is not None:
        where.append(
            or_(
                SitePage.last_crawled_at.is_(None),
                SitePage.last_crawled_at < f.crawled_before,
            )
        )
    if f.crawled_after is not None:
        where.append(SitePage.last_crawled_at > f.crawled_after)
    if f.changed_before is not None:
        where.append(SitePage.content_changed_at < f.changed_before)
    if f.changed_after is not None:
        where.append(SitePage.content_changed_at > f.changed_after)
    if f.published_before is not None:
        where.append(SitePage.published_at < f.published_before)
    if f.published_after is not None:
        where.append(SitePage.published_at > f.published_after)
    return where


VIEW_COLUMNS = {"export": EXPORT, "text": TEXT_VIEW, "slim": SLIM}
VIEW_RECORDS = {
    "export": SitePageExportRecord,
    "text": SitePageTextRecord,
    "slim": SitePageSlimRecord,
}


async def _index_status_by_page(
    db: AsyncSession, page_ids: list[str]
) -> dict[str, SitePageIndexStatus]:
    rows = (
        await db.execute(
            select(SitePageIndexStatus).where(SitePageIndexStatus.page_id.in_(page_ids))
        )
    ).scalars()
    return {st.page_id: st for st in rows}


def _with_index_status(page: SitePageRecord, st: SitePageIndexStatus | None) -> SitePageRecord:
    if st is None:
        return page
    return page.model_copy(
        update={
            "index_state": st.index_state,
            "coverage_state": st.coverage_state,
            "google_canonical": st.google_canonical,
            "index_checked_at": st.index_checked_at,
        }
    )


async def list_pages(
    db: AsyncSession,
    site_id: str,
    f: SitePageFilters,
    paging: PaginationParams,
    view: str | None = None,
    match_ids: list[str] | None = None,
) -> SitePageListResult:
    where = _conditions(site_id, f, match_ids)
    order = _order_by(f.sort_specs(), match_ids)
    limit = paging.page_size
    offset = paging.offset

    if view == "full":
        result = await db.execute(
            select(SitePage).where(*where).order_by(*order).limit(limit).offset(offset)
        )
        full = [SitePageRecord.model_validate(p) for p in result.scalars().all()]
        status_by_page = await _index_status_by_page(db, [p.id for p in full]) if full else {}
        pages = [_with_index_status(p, status_by_page.get(p.id)) for p in full]
    else:
        record = VIEW_RECORDS.get(view or "slim", SitePageSlimRecord)
        cols = VIEW_COLUMNS.get(view or "slim", SLIM)
        result = await db.execute(
            select(*cols).where(*where).order_by(*order).limit(limit).offset(offset)
        )
        pages = [record.model_validate(m) for m in result.mappings().all()]

    total = (
        await db.execute(select(func.count()).select_from(SitePage).where(*where))
    ).scalar_one()
    return SitePageListResult(
        data=pages,
        pagination=PaginationService.build_pagination_meta(
            int(total), paging.page, paging.page_size
        ),
    )


async def crawl_known_pages(
    db: AsyncSession, site_id: str, limit: int = 20_000
) -> list[CrawlKnownPageRecord]:
    rows = (
        await db.execute(
            text(
                f"""
    select url, content_hash, etag, last_modified, last_crawled_at, inlinks,
           ({CRAWL_COMPLETE_SQL}) as crawl_complete
      from site_pages
     where site_id = :site_id
     limit :limit
    """
            ),
            {"site_id": site_id, "limit": limit},
        )
    ).mappings()

    return [
        CrawlKnownPageRecord(
            url=str(r["url"]),
            inlinks=int(r["inlinks"] or 0),
            crawl_complete=r["crawl_complete"] is True,
            content_hash=r["content_hash"],
            etag=r["etag"],
            last_modified=r["last_modified"],
            last_crawled_at=r["last_crawled_at"],
        )
        for r in rows
    ]


async def link_frontier(db: AsyncSession, site_id: str, limit: int = 20_000) -> list[str]:
    rows = (
        await db.execute(
            text(
                """
    select distinct e.dst_url
      from site_page_links e
     where e.site_id = :site_id
       and not e.external
       and not exists (
         select 1 from site_pages t
          where t.site_id = :site_id
            and regexp_replace(t.url, '/+$', '') = e.dst_url
       )
     limit :limit
    """
            ),
            {"site_id": site_id, "limit": limit},
        )
    ).scalars()
    return [str(u) for u in rows]


async def mark_all_unvisited(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        update(SitePage)
        .where(SitePage.site_id == site_id)
        .values(visited=False)
        .returning(SitePage.id)
    )
    return len(result.scalars().all())


async def mark_visited(db: AsyncSession, site_id: str, urls: list[str]) -> int:
    if not urls:
        return 0
    stmt = text(
        """
    update site_pages
       set visited = true
     where site_id = :site_id
       and regexp_replace(url, '/+$', '') in (
             select regexp_replace(u, '/+$', '') from unnest(cast(:urls as text[])) as u
           )
    returning id
    """
    ).bindparams(bindparam("urls", type_=ARRAY(TEXT)))
    result = await db.execute(stmt, {"site_id": site_id, "urls": urls})
    return len(result.scalars().all())


async def delete_unvisited(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        delete(SitePage)
        .where(SitePage.site_id == site_id, SitePage.visited.is_(False))
        .returning(SitePage.id)
    )
    return len(result.scalars().all())


def _page_where(site_id: str, page_id: str | None, url: str | None):
    return [
        SitePage.site_id == site_id,
        SitePage.id == page_id if page_id else SitePage.url == url,
    ]


async def _load_page(
    db: AsyncSession, site_id: str, page_id: str | None = None, url: str | None = None
) -> SitePage | None:
    result = await db.execute(select(SitePage).where(*_page_where(site_id, page_id, url)).limit(1))
    return result.scalars().first()


async def _link_counts(db: AsyncSession, page_id: str) -> tuple[int, int]:
    row = (
        await db.execute(
            select(
                cast(func.count().filter(SitePageLink.external.is_(False)), Integer).label(
                    "internal"
                ),
                cast(func.count().filter(SitePageLink.external.is_(True)), Integer).label(
                    "external"
                ),
            ).where(SitePageLink.src_page_id == page_id)
        )
    ).one()
    return int(row.internal), int(row.external)


async def _as_record(db: AsyncSession, page: SitePage | None) -> SitePageRecord | None:
    if page is None:
        return None
    internal, external = await _link_counts(db, page.id)
    return SitePageRecord.model_validate(page).model_copy(
        update={"out_link_count": internal, "external_link_count": external}
    )


async def get_page(db: AsyncSession, site_id: str, page_id: str) -> SitePageRecord | None:
    return await _as_record(db, await _load_page(db, site_id, page_id=page_id))


async def get_page_by_url(db: AsyncSession, site_id: str, url: str) -> SitePageRecord | None:
    return await _as_record(db, await _load_page(db, site_id, url=url))


LINK_COLUMNS = (
    SitePageLink.id,
    SitePageLink.src_page_id,
    SitePageLink.dst_page_id,
    SitePageLink.dst_url,
    SitePageLink.external,
    SitePageLink.region,
    SitePageLink.rel,
    SitePageLink.anchor,
    SitePageLink.count,
    SitePageLink.followable,
    SitePageLink.dst_canonical,
)


async def page_links(
    db: AsyncSession, site_id: str, page_id: str, cap: int = 500
) -> SitePageLinksResult:
    outbound = (
        await db.execute(
            select(*LINK_COLUMNS)
            .where(SitePageLink.site_id == site_id, SitePageLink.src_page_id == page_id)
            .order_by(SitePageLink.external.asc(), SitePageLink.dst_url.asc())
            .limit(cap)
        )
    ).mappings()
    inbound = (
        await db.execute(
            select(*LINK_COLUMNS, SitePage.url.label("src_url"))
            .join(SitePage, SitePage.id == SitePageLink.src_page_id)
            .where(SitePageLink.site_id == site_id, SitePageLink.dst_page_id == page_id)
            .order_by(SitePage.url.asc())
            .limit(cap)
        )
    ).mappings()
    return SitePageLinksResult(
        inbound=[SitePageLinkRecord.model_validate(r) for r in inbound],
        outbound=[SitePageLinkRecord.model_validate(r) for r in outbound],
    )


async def insert_page(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> SitePageRecord:
    now = datetime.now(UTC)
    page = SitePage(
        **values, id=uid("spg"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now
    )
    db.add(page)
    await db.flush()
    await db.refresh(page)
    return SitePageRecord.model_validate(page)


async def update_page(
    db: AsyncSession, site_id: str, page_id: str, values: dict[str, Any]
) -> SitePageRecord | None:
    page = await _load_page(db, site_id, page_id=page_id)
    if page is None:
        return None
    for key, value in values.items():
        setattr(page, key, value)
    page.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(page)
    return SitePageRecord.model_validate(page)


async def delete_page(db: AsyncSession, site_id: str, page_id: str) -> SitePageRef | None:
    page = await _load_page(db, site_id, page_id=page_id)
    if page is None:
        return None
    removed = SitePageRef(id=page.id, url=page.url)
    await db.delete(page)
    await db.flush()
    return removed


CRAWL_COLUMNS = (
    "status",
    "content_hash",
    "etag",
    "last_modified",
    "last_crawled_at",
    "title",
    "title_pixels",
    "meta_description",
    "h1",
    "headings",
    "body_text",
    "canonical",
    "robots_directives",
    "x_robots_tag",
    "blocked_by_robots",
    "viewport_meta",
    "nosnippet_count",
    "social_meta_count",
    "social_meta",
    "has_google_analytics",
    "author",
    "schema_types",
    "schema_nodes",
    "lang",
    "hreflang",
    "format",
    "in_sitemap",
    "redirect_to",
    "redirect_final",
    "redirect_hops",
    "fetch_error",
    "content_type",
    "images",
    "published_at",
    "modified_at",
    "word_count",
    "mixed_content",
    "shallow",
    "shallow_reason",
)


async def upsert_pages(
    db: AsyncSession, user_id: str, site_id: str, items: list[SitePageCrawlItem]
) -> list[SitePageRef]:
    if not items:
        return []
    now = datetime.now(UTC)

    deduped: dict[str, dict[str, Any]] = {}
    links_by_url: dict[str, list[PageLinkInput]] = {}
    for item in items:
        url = item.url
        if url.strip() == "":
            continue
        if item.links is not None:
            links_by_url[url] = item.links
        row = item.changes()
        if "content_hash" in row:
            row["content_changed_at"] = now
        row.update(id=uid("spg"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now)
        deduped[url] = row
    values = list(deduped.values())
    if not values:
        return []

    buckets: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for v in values:
        signature = tuple(sorted(v.keys()))
        buckets.setdefault(signature, []).append(v)

    written: list[SitePageRef] = []
    for signature, rows in buckets.items():
        crawled = [c for c in CRAWL_COLUMNS if c in signature]
        stmt = pg_insert(SitePage).values(rows)
        set_: dict[str, Any] = {"updated_at": now, "visited": True}
        for c in crawled:
            set_[c] = getattr(stmt.excluded, c)
        if "content_hash" in crawled:
            set_["content_changed_at"] = case(
                (
                    SitePage.content_hash.is_distinct_from(stmt.excluded.content_hash),
                    stmt.excluded.content_changed_at,
                ),
                else_=SitePage.content_changed_at,
            )
        stmt = stmt.on_conflict_do_update(
            index_elements=[SitePage.site_id, SitePage.url], set_=set_
        ).returning(SitePage.id, SitePage.url)
        result = await db.execute(stmt)
        written.extend(SitePageRef(id=r.id, url=r.url) for r in result)

    if links_by_url:
        by_page = {ref.id: links_by_url[ref.url] for ref in written if ref.url in links_by_url}
        await replace_page_links(db, user_id, site_id, by_page)
    return written


NORMALISE_LINK_URL_SQL = """regexp_replace(regexp_replace(:url, '#.*$', ''), '/+$', '')"""

DST_CANONICAL_SQL = """t.status between 200 and 299
  and not t.blocked_by_robots
  and coalesce(t.robots_directives, '') not ilike '%noindex%'
  and coalesce(t.x_robots_tag, '') not ilike '%noindex%'
  and (t.canonical is null or regexp_replace(t.canonical, '/+$', '') = regexp_replace(t.url, '/+$', ''))
  and t.redirect_to is null"""

LINK_REGIONS = ("body", "nav", "header", "footer", "aside", "breadcrumb", "pagination")


def _link_region(region: str | None) -> str:
    wanted = (region or "").strip().lower()
    return wanted if wanted in LINK_REGIONS else "body"


async def replace_page_links(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    links_by_page: dict[str, list[PageLinkInput]],
) -> int:
    if not links_by_page:
        return 0
    now = datetime.now(UTC)
    page_ids = list(links_by_page)
    await db.execute(
        delete(SitePageLink).where(
            SitePageLink.site_id == site_id, SitePageLink.src_page_id.in_(page_ids)
        )
    )

    rows: list[dict[str, Any]] = []
    for page_id, links in links_by_page.items():
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for link in links:
            target = normalise_url(link.url)
            if target == "":
                continue
            region = _link_region(link.region)
            key = (target, region)
            existing = merged.get(key)
            count = max(link.count, 1)
            if existing is None:
                merged[key] = {
                    "id": uid("spl"),
                    "user_id": user_id,
                    "site_id": site_id,
                    "src_page_id": page_id,
                    "dst_page_id": None,
                    "dst_url": target,
                    "external": link.external,
                    "region": region,
                    "rel": link.rel,
                    "anchor": link.anchor,
                    "count": count,
                    "followable": _followable(link.rel),
                    "dst_canonical": True,
                    "created_at": now,
                    "updated_at": now,
                }
                continue
            existing["count"] += count
            existing["followable"] = existing["followable"] or _followable(link.rel)
            if existing["anchor"] is None:
                existing["anchor"] = link.anchor
        rows.extend(merged.values())

    if not rows:
        return 0
    for chunk in (rows[i : i + 1000] for i in range(0, len(rows), 1000)):
        await db.execute(pg_insert(SitePageLink).values(chunk))
    return len(rows)


def _followable(rel: str | None) -> bool:
    return "nofollow" not in (rel or "").lower()


async def resolve_links(db: AsyncSession, site_id: str) -> None:
    await db.execute(
        text(
            f"""
    update site_page_links e
       set dst_page_id = t.id,
           dst_canonical = ({DST_CANONICAL_SQL}),
           updated_at = now()
      from site_pages t
     where e.site_id = :site_id
       and not e.external
       and t.site_id = :site_id
       and regexp_replace(t.url, '/+$', '') = e.dst_url
       and t.id <> e.src_page_id
    """
        ),
        {"site_id": site_id},
    )
    await db.execute(
        text(
            f"""
    update site_page_links e
       set dst_page_id = null,
           dst_canonical = true,
           updated_at = now()
     where e.site_id = :site_id
       and (e.external
            or not exists (
              select 1 from site_pages t
               where t.site_id = :site_id
                 and regexp_replace(t.url, '/+$', '') = e.dst_url
                 and t.id <> e.src_page_id
            ))
    """
        ),
        {"site_id": site_id},
    )


async def restamp_graph(db: AsyncSession, site_id: str) -> None:
    await db.execute(
        text(
            """
    with recursive edges as (
      select e.src_page_id as src, e.dst_page_id as dst, e.region
        from site_page_links e
       where e.site_id = :site_id and e.dst_page_id is not null
    ),
    inbound as (
      select dst, count(distinct src)::int as inlinks
        from edges
       group by dst
    ),
    home as (
      select id
        from site_pages
       where site_id = :site_id and regexp_replace(url, '^https?://[^/]+', '') in ('', '/')
       order by length(url)
       limit 1
    ),
    reach(id, depth) as (
      select id, 0 from home
      union
      select e.dst, r.depth + 1
        from edges e join reach r on e.src = r.id
       where r.depth < 50 and e.region <> 'pagination'
    ),
    depths as (select id, min(depth)::int as depth from reach group by id)
    update site_pages p
       set inlinks = coalesce(i.inlinks, 0),
           depth = d.depth,
           updated_at = now()
      from site_pages k
      left join inbound i on i.dst = k.id
      left join depths d on d.id = k.id
     where k.site_id = :site_id and p.id = k.id
    """
        ),
        {"site_id": site_id},
    )


LIVE_PAGE = "p.status between 200 and 299 and not p.blocked_by_robots"


async def live_page_refs(db: AsyncSession, site_id: str) -> list[SitePageRef]:
    rows = (
        await db.execute(
            text(
                f"""
    select p.id, p.url from site_pages p
     where p.site_id = :site_id and {LIVE_PAGE}
    """
            ),
            {"site_id": site_id},
        )
    ).mappings()
    return [SitePageRef(id=str(r["id"]), url=str(r["url"])) for r in rows]


async def edge_list(db: AsyncSession, site_id: str) -> list[SitePageEdge]:
    rows = (
        await db.execute(
            text(
                f"""
    select distinct e.src_page_id as src, e.dst_page_id as dst
      from site_page_links e
      join site_pages p on p.id = e.src_page_id
     where e.site_id = :site_id and e.dst_page_id is not null
       and e.followable and e.dst_canonical and {LIVE_PAGE}
    """
            ),
            {"site_id": site_id},
        )
    ).mappings()
    return [SitePageEdge(src=str(r["src"]), dst=str(r["dst"])) for r in rows]


async def landing_seed(db: AsyncSession, site_id: str) -> SitePageLandingSeed:
    rows = (
        await db.execute(
            text(
                """
    select landing_page as path, sum(sessions)::int as sessions
      from site_traffic_landing_daily
     where site_id = :site_id
       and day >= current_date - interval '90 days'
     group by 1
    """
            ),
            {"site_id": site_id},
        )
    ).mappings()
    return SitePageLandingSeed(sessions_by_path={str(r["path"]): int(r["sessions"]) for r in rows})


SCORE_COLUMNS = ("link_score",)


async def write_scores(
    db: AsyncSession, site_id: str, column: str, scores: dict[str, float]
) -> None:
    if column not in SCORE_COLUMNS:
        raise ValueError(f"{column} is not a score column")
    await db.execute(
        text(
            f"""
    update site_pages set {column} = null
     where site_id = :site_id and {column} is not null
    """
        ),
        {"site_id": site_id},
    )
    entries = list(scores.items())
    for start in range(0, len(entries), 1000):
        chunk = entries[start : start + 1000]
        placeholders = ", ".join(f"(:id{i}, :score{i})" for i in range(len(chunk)))
        params: dict[str, Any] = {"site_id": site_id}
        for i, (page_id, score) in enumerate(chunk):
            params[f"id{i}"] = page_id
            params[f"score{i}"] = score
        await db.execute(
            text(
                f"""
      update site_pages p
         set {column} = v.score::real
        from (values {placeholders}) as v(id, score)
       where p.site_id = :site_id and p.id = v.id
    """
            ),
            params,
        )


async def stamp_sitemap_presence(
    db: AsyncSession, site_id: str, sitemap_urls: list[str]
) -> SitemapPresenceResult:
    stmt = text(
        """
    update site_pages
       set in_sitemap = url = any(cast(:urls as text[])), updated_at = now()
     where site_id = :site_id
    returning in_sitemap
    """
    ).bindparams(bindparam("urls", type_=ARRAY(TEXT)))
    rows = (await db.execute(stmt, {"site_id": site_id, "urls": sitemap_urls})).scalars().all()
    return SitemapPresenceResult(known=len(rows), listed=sum(1 for r in rows if r))


async def crawl_counts(db: AsyncSession, site_id: str) -> CrawlCountsResult:
    n = (
        await db.execute(
            select(func.count()).select_from(SitePage).where(SitePage.site_id == site_id)
        )
    ).scalar_one()
    return CrawlCountsResult(pages=int(n))


def _cnt(cond):
    return cast(func.count().filter(cond), Integer)


async def page_stats(db: AsyncSession, site_id: str) -> SitePageStatsRecord:
    row = (
        (
            await db.execute(
                select(
                    _cnt(~SitePage.blocked_by_robots).label("pages"),
                    _cnt(SitePage.blocked_by_robots).label("blockedByRobots"),
                    _cnt(
                        and_(
                            SitePage.blocked_by_robots,
                            or_(SitePage.in_sitemap, SitePage.inlinks > 0),
                        )
                    ).label("blockedAndDiscoverable"),
                    _cnt(SitePage.status == 200).label("ok"),
                    _cnt(
                        and_(
                            or_(SitePage.status >= 400, SitePage.status == 0),
                            SitePage.status.not_in((404, 410)),
                        )
                    ).label("errored"),
                    _cnt(SitePage.status.in_((404, 410))).label("gone"),
                    _cnt(and_(~SitePage.in_sitemap, SitePage.status == 200)).label("notInSitemap"),
                    _cnt(and_(SitePage.in_sitemap, SitePage.status.in_((404, 410)))).label(
                        "sitemapMissing"
                    ),
                    _cnt(SitePage.status == 404).label("notFound"),
                    _cnt(SitePage.status.in_((401, 403, 429))).label("blocked"),
                    _cnt(SitePage.status >= 500).label("serverError"),
                    _cnt(SitePage.status == 0).label("unreachable"),
                    _cnt(
                        and_(
                            SitePage.in_sitemap,
                            SitePage.inlinks == 0,
                            SitePage.status == 200,
                        )
                    ).label("orphans"),
                    _cnt(SitePage.shallow).label("shallow"),
                    _cnt(SitePage.embed_state == "failed").label("embedFailed"),
                    _cnt(text(f"({CRAWL_COMPLETE_SQL})")).label("crawlComplete"),
                )
                .select_from(SitePage)
                .where(SitePage.site_id == site_id)
            )
        )
        .mappings()
        .one()
    )

    by_stage = (
        await db.execute(
            text(
                """
    select case
             when blocked_by_robots then 'blocked'
             when status is null then 'pending'
             when status >= 400 or status = 0 then 'failed'
             when shallow then 'skipped'
             when body_text is null or chunked_from_hash is null
               or chunked_from_hash is distinct from content_hash then 'crawled'
             else 'indexed'
           end as stage,
           count(*)::int as n
      from site_pages where site_id = :site_id
     group by 1
    """
            ),
            {"site_id": site_id},
        )
    ).mappings()

    by_page_type = (
        await db.execute(
            select(SitePageLlmExtraction.page_type, cast(func.count(), Integer).label("n"))
            .select_from(SitePage)
            .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id)
            .where(SitePage.site_id == site_id)
            .group_by(SitePageLlmExtraction.page_type)
        )
    ).mappings()

    by_shallow_reason = (
        await db.execute(
            select(SitePage.shallow_reason, cast(func.count(), Integer).label("n"))
            .where(SitePage.site_id == site_id, SitePage.shallow.is_(True))
            .group_by(SitePage.shallow_reason)
        )
    ).mappings()

    chunks = (
        (
            await db.execute(
                select(
                    cast(func.count(), Integer).label("total"),
                    _cnt(SiteChunk.embedding.is_not(None)).label("embedded"),
                    _cnt(SiteChunk.embed_error.is_not(None)).label("failed"),
                )
                .select_from(SiteChunk)
                .where(SiteChunk.site_id == site_id)
            )
        )
        .mappings()
        .one()
    )

    return SitePageStatsRecord(
        **dict(row),
        by_stage=[StageCount(stage=r["stage"], n=r["n"]) for r in by_stage],
        by_page_type=[PageTypeCount(page_type=r["page_type"], n=r["n"]) for r in by_page_type],
        by_shallow_reason=[
            ShallowReasonCount(reason=r["shallow_reason"], n=r["n"]) for r in by_shallow_reason
        ],
        chunks=ChunkCounts.model_validate(dict(chunks)),
    )


DISCOVERY_COLUMNS = (
    SitePage.id,
    SitePage.url,
    SitePage.title,
    PAGE_TYPE,
    SitePage.inlinks,
    SitePage.depth,
    SitePage.in_sitemap,
)

LIVE = and_(SitePage.status.between(200, 299), ~SitePage.blocked_by_robots)
ORPHAN = and_(LIVE, SitePage.inlinks == 0, SitePage.depth.is_distinct_from(0))
UNREACHABLE = and_(LIVE, SitePage.inlinks > 0, SitePage.depth.is_(None))


async def _discovery_pages(
    db: AsyncSession, site_id: str, cond, order, cap: int
) -> list[DiscoveryPage]:
    rows = (
        await db.execute(
            select(*DISCOVERY_COLUMNS)
            .where(SitePage.site_id == site_id, cond)
            .order_by(*order)
            .limit(cap)
        )
    ).mappings()
    return [DiscoveryPage.model_validate(dict(r)) for r in rows]


async def page_discovery(
    db: AsyncSession, site_id: str, deep_from: int, cap: int
) -> SitePageDiscoveryRecord:
    deep = and_(LIVE, SitePage.depth >= deep_from)
    row = (
        (
            await db.execute(
                select(
                    _cnt(LIVE).label("live"),
                    _cnt(and_(LIVE, SitePage.depth == 0)).label("home"),
                    _cnt(ORPHAN).label("orphans"),
                    _cnt(UNREACHABLE).label("unreachable"),
                    _cnt(deep).label("deep"),
                )
                .select_from(SitePage)
                .where(SitePage.site_id == site_id)
            )
        )
        .mappings()
        .one()
    )
    by_depth = (
        await db.execute(
            select(SitePage.depth, cast(func.count(), Integer).label("n"))
            .where(SitePage.site_id == site_id, LIVE)
            .group_by(SitePage.depth)
            .order_by(SitePage.depth.asc().nulls_last())
        )
    ).mappings()
    return SitePageDiscoveryRecord(
        live=row["live"],
        home_found=row["home"] > 0,
        orphans=row["orphans"],
        unreachable=row["unreachable"],
        deep=row["deep"],
        deep_from=deep_from,
        by_depth=[DepthCount(depth=r["depth"], n=r["n"]) for r in by_depth],
        orphan_pages=await _discovery_pages(
            db, site_id, ORPHAN, [SitePage.in_sitemap.desc(), SitePage.url.asc()], cap
        ),
        unreachable_pages=await _discovery_pages(
            db, site_id, UNREACHABLE, [SitePage.inlinks.asc(), SitePage.url.asc()], cap
        ),
        deep_pages=await _discovery_pages(
            db,
            site_id,
            deep,
            [SitePage.depth.desc(), SitePage.inlinks.asc(), SitePage.url.asc()],
            cap,
        ),
    )


CHUNK_COLUMNS = (
    SiteChunk.id,
    SiteChunk.site_id,
    SiteChunk.page_id,
    SiteChunk.ordinal,
    SiteChunk.heading_path,
    SiteChunk.text,
    SiteChunk.embed_model,
    SiteChunk.embed_attempts,
    SiteChunk.embed_error,
    SiteChunk.from_hash,
    SiteChunk.created_at,
    SiteChunk.updated_at,
)


async def list_chunks(db: AsyncSession, site_id: str, page_id: str) -> list[SiteChunkRecord]:
    rows = (
        await db.execute(
            select(*CHUNK_COLUMNS)
            .where(SiteChunk.site_id == site_id, SiteChunk.page_id == page_id)
            .order_by(SiteChunk.ordinal.asc())
        )
    ).mappings()
    return [SiteChunkRecord.model_validate(r) for r in rows]
