import json
import os
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
from src.site_pages.models.site_page_index_status import SitePageIndexStatus
from src.site_pages.schemas import (
    ChunkCounts,
    CrawlCountsResult,
    CrawlKnownPageRecord,
    KindCount,
    SemanticPageMatch,
    ShallowReasonCount,
    SiteChunkRecord,
    SitemapPresenceResult,
    SitePageCrawlItem,
    SitePageEdge,
    SitePageExportRecord,
    SitePageFilters,
    SitePageKeywordCoverageResult,
    SitePageLandingSeed,
    SitePageListResult,
    SitePageRecord,
    SitePageRef,
    SitePageSlimRecord,
    SitePageStatsRecord,
    SitePageTextRecord,
    StageCount,
    TermCount,
)
from src.site_pages.stage import CRAWL_COMPLETE_SQL, STAGE_SQL

NEEDS_AUDIT = and_(SitePage.status == 200, SitePage.content_hash.is_not(None))

SLIM = (
    SitePage.id,
    SitePage.site_id,
    SitePage.chunked_from_hash,
    SitePage.url,
    SitePage.title,
    SitePage.kind,
    SitePage.status,
    SitePage.inlinks,
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

IMAGE_BYTES_SQL = text(
    """(select coalesce(sum((im->>'bytes')::bigint), 0)
    from jsonb_array_elements(site_pages.images) im where im->>'bytes' is not null)::int"""
).columns(image_bytes=Integer)

EXPORT = (
    SitePage.url,
    SitePage.status,
    SitePage.kind,
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
    SitePage.has_viewport,
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
    cast(func.jsonb_array_length(SitePage.out_links), Integer).label("out_link_count"),
    cast(func.jsonb_array_length(SitePage.external_links), Integer).label("external_link_count"),
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
    if f.kind:
        where.append(SitePage.kind == f.kind)
    if f.kinds:
        where.append(SitePage.kind.in_(f.kinds))
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


def _grouped(column, where, cap: int):
    sub = (
        select(SitePage.id.label("page_id"), func.unnest(column).label("value"))
        .where(*where)
        .subquery()
    )
    return (
        select(
            sub.c.value.label("value"),
            cast(func.count(func.distinct(sub.c.page_id)), Integer).label("pages"),
        )
        .group_by(sub.c.value)
        .order_by(text("pages desc"), text("value asc"))
        .limit(cap + 1)
    )


async def keyword_coverage(
    db: AsyncSession, site_id: str, f: SitePageFilters, limit: int = 500
) -> SitePageKeywordCoverageResult:
    where = _conditions(site_id, f)
    cap = min(max(limit, 1), 2000)

    kw = [
        TermCount.model_validate(m)
        for m in (await db.execute(_grouped(SitePage.keywords, where, cap))).mappings()
    ]
    qs = [
        TermCount.model_validate(m)
        for m in (await db.execute(_grouped(SitePage.questions_answered, where, cap))).mappings()
    ]
    counts = (
        await db.execute(
            select(
                cast(func.count(), Integer).label("matched"),
                cast(
                    func.count().filter(
                        or_(
                            func.coalesce(func.cardinality(SitePage.keywords), 0) > 0,
                            func.coalesce(func.cardinality(SitePage.questions_answered), 0) > 0,
                        )
                    ),
                    Integer,
                ).label("annotated"),
            )
            .select_from(SitePage)
            .where(*where)
        )
    ).one()

    return SitePageKeywordCoverageResult(
        keywords=kw[:cap],
        questions=qs[:cap],
        keywords_truncated=len(kw) > cap,
        questions_truncated=len(qs) > cap,
        matched_pages=counts.matched,
        annotated_pages=counts.annotated,
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
    select distinct l->>'url' as url
      from site_pages p, lateral jsonb_array_elements(p.out_links) l
     where p.site_id = :site_id
       and not exists (
         select 1 from site_pages t
          where t.site_id = :site_id
            and regexp_replace(t.url, '/+$', '') = regexp_replace(l->>'url', '/+$', '')
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


async def get_page(db: AsyncSession, site_id: str, page_id: str) -> SitePageRecord | None:
    page = await _load_page(db, site_id, page_id=page_id)
    return None if page is None else SitePageRecord.model_validate(page)


async def get_page_by_url(db: AsyncSession, site_id: str, url: str) -> SitePageRecord | None:
    page = await _load_page(db, site_id, url=url)
    return None if page is None else SitePageRecord.model_validate(page)


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
    "out_links",
    "external_links",
    "canonical",
    "robots_directives",
    "x_robots_tag",
    "blocked_by_robots",
    "has_viewport",
    "author",
    "schema_types",
    "schema_nodes",
    "lang",
    "hreflang",
    "kind",
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
    for item in items:
        url = item.url
        if url.strip() == "":
            continue
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
    return written


OUT_LINK_URL = """lateral (
  select regexp_replace(regexp_replace(l->>'url', '#.*$', ''), '/+$', '') as u
) x"""

NORM_OUT_LINK = """coalesce(
  lower(substring(x.u from '^([A-Za-z][A-Za-z0-9+.-]*://[^/]*)')) ||
  coalesce(substring(x.u from '^[A-Za-z][A-Za-z0-9+.-]*://[^/]*(/.*)$'), ''),
  x.u)"""


async def rebuild_graph(db: AsyncSession, site_id: str) -> None:
    await db.execute(
        text(
            f"""
    with recursive links as (
      select regexp_replace(p.url, '/+$', '') as src,
             {NORM_OUT_LINK} as dst,
             l->>'anchor' as anchor
        from site_pages p, lateral jsonb_array_elements(p.out_links) l, {OUT_LINK_URL}
       where p.site_id = :site_id
    ),
    edges as (
      select distinct l.src, l.dst, l.anchor
        from links l
        join site_pages t
          on t.site_id = :site_id and regexp_replace(t.url, '/+$', '') = l.dst
       where l.src <> l.dst
    ),
    inbound as (
      select dst as url,
             count(*)::int as inlinks,
             jsonb_agg(jsonb_build_object('from', src, 'anchor', anchor))
               filter (where rn <= 25) as anchors
        from (select src, dst, anchor, row_number() over (partition by dst order by src) as rn
                from edges) ranked
       group by dst
    ),
    home as (
      select regexp_replace(url, '/+$', '') as key
        from site_pages
       where site_id = :site_id and regexp_replace(url, '^https?://[^/]+', '') in ('', '/')
       order by length(url)
       limit 1
    ),
    reach(url, depth) as (
      select key, 0 from home
      union
      select e.dst, r.depth + 1 from edges e join reach r on e.src = r.url where r.depth < 50
    ),
    depths as (select url, min(depth)::int as depth from reach group by url)
    update site_pages p
       set inlinks = coalesce(i.inlinks, 0),
           inbound_anchors = coalesce(i.anchors, '[]'::jsonb),
           depth = d.depth,
           updated_at = now()
      from (select id, regexp_replace(url, '/+$', '') as key from site_pages
             where site_id = :site_id) k
      left join inbound i on i.url = k.key
      left join depths d on d.url = k.key
     where p.id = k.id
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
    with links as (
      select p.id as src, {NORM_OUT_LINK} as dst_url
        from site_pages p, lateral jsonb_array_elements(p.out_links) l, {OUT_LINK_URL}
       where p.site_id = :site_id and {LIVE_PAGE}
    )
    select distinct l.src, t.id as dst
      from links l
      join site_pages t
        on t.site_id = :site_id
       and regexp_replace(t.url, '/+$', '') = l.dst_url
       and t.status between 200 and 299 and not t.blocked_by_robots
     where l.src <> t.id
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


async def write_link_scores(db: AsyncSession, site_id: str, scores: dict[str, float]) -> None:
    await db.execute(
        text(
            """
    update site_pages set link_score = null
     where site_id = :site_id and link_score is not null
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
         set link_score = v.score::real
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

    by_kind = (
        await db.execute(
            select(SitePage.kind, cast(func.count(), Integer).label("n"))
            .where(SitePage.site_id == site_id)
            .group_by(SitePage.kind)
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
        by_kind=[KindCount(kind=r["kind"], n=r["n"]) for r in by_kind],
        by_shallow_reason=[
            ShallowReasonCount(reason=r["shallow_reason"], n=r["n"]) for r in by_shallow_reason
        ],
        chunks=ChunkCounts.model_validate(dict(chunks)),
    )


CHUNK_COLUMNS = (
    SiteChunk.id,
    SiteChunk.site_id,
    SiteChunk.page_id,
    SiteChunk.ordinal,
    SiteChunk.heading_path,
    SiteChunk.text,
    SiteChunk.embed_model,
    SiteChunk.embedded_from_hash,
    SiteChunk.embed_attempts,
    SiteChunk.embed_error,
    SiteChunk.chunk_strategy,
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


MIN_SIMILARITY = float(os.environ.get("MEELU_SEARCH_MIN_SIMILARITY", "0.82"))


async def semantic_page_matches(
    db: AsyncSession,
    site_id: str,
    embedding: list[float],
    model: str | None = None,
    pool: int | None = None,
) -> list[SemanticPageMatch]:
    vec = json.dumps(embedding)
    capped = min(max(pool if pool is not None else 500, 1), 2000)

    rows = (
        await db.execute(
            text(
                """
    with hits as (
      select c.page_id, c.text, c.heading_path,
             1 - (c.embedding <=> cast(:vec as vector)) as similarity,
             row_number() over (
               partition by c.page_id order by c.embedding <=> cast(:vec as vector)
             ) as per_page
        from site_chunks c
       where c.site_id = :site_id
         and c.embedding is not null
         and c.embed_model is not distinct from cast(:model as text)
         and 1 - (c.embedding <=> cast(:vec as vector)) >= :min_similarity
    )
    select page_id, text, heading_path, similarity
      from hits where per_page = 1
     order by similarity desc
     limit :pool
    """
            ),
            {
                "site_id": site_id,
                "vec": vec,
                "model": model,
                "min_similarity": MIN_SIMILARITY,
                "pool": capped,
            },
        )
    ).mappings()

    return [
        SemanticPageMatch(
            page_id=str(r["page_id"]),
            similarity=float(r["similarity"]),
            snippet=r["text"],
            heading_path=r["heading_path"],
        )
        for r in rows
    ]
