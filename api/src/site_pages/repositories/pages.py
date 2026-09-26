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
from src.site_pages.models.site_page import SitePage
from src.site_pages.schemas import (
    CrawlKnownPageRecord,
    DepthCount,
    DiscoveryPage,
    RenderEligiblePage,
    ShallowReasonCount,
    SitemapPresenceResult,
    SitePageBrief,
    SitePageChunkSource,
    SitePageCountsRecord,
    SitePageCrawlItem,
    SitePageDiscoveryRecord,
    SitePageExportRecord,
    SitePageFilters,
    SitePageListResult,
    SitePageRecord,
    SitePageRef,
    SitePageSlimRecord,
    SitePageTextRecord,
    StageCount,
)
from src.site_pages.schemas.llm_extraction import PendingPageRecord

STAGE_SQL = {
    "pending": "status is null and not blocked_by_robots",
    "blocked": "blocked_by_robots",
    "failed": "status >= 400 or status = 0",
    "skipped": "status = 200 and shallow",
    "crawled": """status = 200 and not shallow and (body_text is null
             or chunked_from_hash is null
             or chunked_from_hash is distinct from content_hash)""",
    "indexed": """status = 200 and not shallow and body_text is not null
             and chunked_from_hash is not distinct from content_hash""",
}

CRAWL_COMPLETE_SQL = f"""(({STAGE_SQL["indexed"]})
      or ({STAGE_SQL["skipped"]})
      or ({STAGE_SQL["blocked"]}))
     and embed_state is distinct from 'failed'"""

NEEDS_AUDIT = and_(SitePage.status == 200, SitePage.content_hash.is_not(None))

SLIM = (
    SitePage.id,
    SitePage.site_id,
    SitePage.chunked_from_hash,
    SitePage.url,
    SitePage.title,
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

IMAGE_BYTES_SQL = text(
    """(select coalesce(sum((im->>'bytes')::bigint), 0)
    from jsonb_array_elements(site_pages.images) im where im->>'bytes' is not null)::int"""
).columns(image_bytes=Integer)

EXPORT = (
    SitePage.id,
    SitePage.url,
    SitePage.status,
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


VIEW_COLUMNS = {"export": EXPORT, "text": TEXT_VIEW, "slim": SLIM}
VIEW_RECORDS = {
    "export": SitePageExportRecord,
    "text": SitePageTextRecord,
    "slim": SitePageSlimRecord,
}


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

SCORE_COLUMNS = ("link_score",)

STRIPPED_URL = func.regexp_replace(SitePage.url, "/+$", "")
URL_PATH = func.regexp_replace(func.regexp_replace(SitePage.url, "^https?://[^/]+", ""), "/+$", "")

LIVE = and_(SitePage.status.between(200, 299), ~SitePage.blocked_by_robots)
ORPHAN = and_(LIVE, SitePage.inlinks == 0, SitePage.depth.is_distinct_from(0))
UNREACHABLE = and_(LIVE, SitePage.inlinks > 0, SitePage.depth.is_(None))
GONE = or_(
    SitePage.status.is_(None),
    SitePage.status >= 300,
    SitePage.redirect_to.is_not(None),
    SitePage.blocked_by_robots.is_(True),
)
EXTRACTABLE = and_(
    SitePage.body_text.is_not(None),
    SitePage.body_text != "",
    SitePage.content_hash.is_not(None),
)
RENDER_ELIGIBLE = and_(
    SitePage.status == 200,
    SitePage.shallow.is_(False),
    SitePage.blocked_by_robots.is_(False),
)

DISCOVERY_COLUMNS = (
    SitePage.id,
    SitePage.url,
    SitePage.title,
    SitePage.inlinks,
    SitePage.depth,
    SitePage.in_sitemap,
)

BRIEF_COLUMNS = (
    SitePage.id,
    SitePage.user_id,
    SitePage.site_id,
    SitePage.url,
    SitePage.title,
    SitePage.meta_description,
    SitePage.h1,
    SitePage.status,
    SitePage.inlinks,
    SitePage.depth,
    SitePage.word_count,
    SitePage.content_hash,
    SitePage.redirect_to,
    SitePage.fetch_error,
    SitePage.blocked_by_robots,
)

CHUNK_SOURCE_COLUMNS = (
    SitePage.id,
    SitePage.site_id,
    SitePage.user_id,
    SitePage.url,
    SitePage.title,
    SitePage.h1,
    SitePage.meta_description,
    SitePage.body_text,
    SitePage.content_hash,
)

WRITE_BATCH = 1000


class SitePageRepository:
    ID_PREFIX = "spg"

    async def list_filtered(
        self,
        db: AsyncSession,
        site_id: str,
        f: SitePageFilters,
        paging: PaginationParams,
        view: str | None = None,
        match_ids: list[str] | None = None,
        page_ids: list[str] | None = None,
    ) -> SitePageListResult:
        where = self._conditions(site_id, f, match_ids, page_ids)
        order = self._order_by(f.sort_specs(), match_ids)
        limit = paging.page_size
        offset = paging.offset

        if view == "full":
            result = await db.execute(
                select(SitePage).where(*where).order_by(*order).limit(limit).offset(offset)
            )
            pages = [SitePageRecord.model_validate(p) for p in result.scalars().all()]
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

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[SitePageRecord]:
        rows = (
            await db.execute(
                select(SitePage).where(SitePage.site_id == site_id).order_by(SitePage.seq.asc())
            )
        ).scalars()
        return [SitePageRecord.model_validate(p) for p in rows]

    async def get(self, db: AsyncSession, site_id: str, page_id: str) -> SitePageRecord | None:
        return self._record(await self._load(db, site_id, page_id=page_id))

    async def get_by_url(self, db: AsyncSession, site_id: str, url: str) -> SitePageRecord | None:
        return self._record(await self._load(db, site_id, url=url))

    async def exists(self, db: AsyncSession, site_id: str, page_id: str) -> bool:
        return bool(await self.existing_ids(db, site_id, [page_id]))

    async def existing_ids(self, db: AsyncSession, site_id: str, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        rows = await db.execute(
            select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id.in_(ids))
        )
        return set(rows.scalars().all())

    async def id_by_url(self, db: AsyncSession, site_id: str, url: str) -> str | None:
        return (await self.ids_by_urls(db, site_id, [url])).get(url)

    async def ids_by_urls(self, db: AsyncSession, site_id: str, urls: list[str]) -> dict[str, str]:
        if not urls:
            return {}
        rows = await db.execute(
            select(SitePage.url, SitePage.id).where(
                SitePage.site_id == site_id, SitePage.url.in_(set(urls))
            )
        )
        return {r.url: r.id for r in rows}

    async def ids_by_url_substring(self, db: AsyncSession, site_id: str, needle: str) -> list[str]:
        rows = await db.execute(
            select(SitePage.id).where(
                SitePage.site_id == site_id, SitePage.url.ilike(f"%{needle}%")
            )
        )
        return list(rows.scalars().all())

    async def urls_by_ids(self, db: AsyncSession, site_id: str, ids: list[str]) -> dict[str, str]:
        if not ids:
            return {}
        rows = await db.execute(
            select(SitePage.id, SitePage.url).where(
                SitePage.site_id == site_id, SitePage.id.in_(set(ids))
            )
        )
        return {r.id: r.url for r in rows}

    async def list_refs_by_ids(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> list[SitePageRef]:
        return [
            SitePageRef(id=page_id, url=url)
            for page_id, url in (await self.urls_by_ids(db, site_id, ids)).items()
        ]

    async def content_hashes_by_ids(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> dict[str, str | None]:
        if not ids:
            return {}
        rows = await db.execute(
            select(SitePage.id, SitePage.content_hash).where(
                SitePage.site_id == site_id, SitePage.id.in_(set(ids))
            )
        )
        return {r.id: r.content_hash for r in rows}

    async def list_by_ids(
        self,
        db: AsyncSession,
        site_id: str | None,
        ids: list[str],
        body_chars: int | None = None,
    ) -> list[SitePageBrief]:
        if not ids:
            return []
        conds: list[Any] = [SitePage.id.in_(set(ids))]
        if site_id is not None:
            conds.append(SitePage.site_id == site_id)
        return await self._briefs(db, conds, body_chars=body_chars)

    async def list_by_urls(
        self,
        db: AsyncSession,
        site_id: str,
        urls: list[str],
        strip_trailing_slash: bool = True,
    ) -> list[SitePageBrief]:
        if not urls:
            return []
        if strip_trailing_slash:
            wanted = {u.rstrip("/") for u in urls}
            cond = STRIPPED_URL.in_(wanted)
        else:
            cond = SitePage.url.in_(set(urls))
        return await self._briefs(db, [SitePage.site_id == site_id, cond])

    async def list_by_paths(
        self, db: AsyncSession, site_id: str, paths: list[str]
    ) -> list[SitePageBrief]:
        if not paths:
            return []
        wanted = {p.rstrip("/") for p in paths}
        return await self._briefs(db, [SitePage.site_id == site_id, URL_PATH.in_(wanted)])

    async def list_briefs(self, db: AsyncSession, site_id: str) -> list[SitePageBrief]:
        return await self._briefs(db, [SitePage.site_id == site_id])

    async def list_live(self, db: AsyncSession, site_id: str) -> list[SitePageBrief]:
        return await self._briefs(db, [SitePage.site_id == site_id, LIVE])

    async def list_not_gone(self, db: AsyncSession, site_id: str) -> list[SitePageBrief]:
        return await self._briefs(db, [SitePage.site_id == site_id, ~GONE])

    async def live_page_refs(self, db: AsyncSession, site_id: str) -> list[SitePageRef]:
        rows = await db.execute(
            select(SitePage.id, SitePage.url).where(SitePage.site_id == site_id, LIVE)
        )
        return [SitePageRef(id=r.id, url=r.url) for r in rows]

    async def live_ids(self, db: AsyncSession, site_id: str) -> set[str]:
        rows = await db.execute(select(SitePage.id).where(SitePage.site_id == site_id, LIVE))
        return set(rows.scalars().all())

    async def gone_ids(self, db: AsyncSession, site_id: str) -> set[str]:
        rows = await db.execute(select(SitePage.id).where(SitePage.site_id == site_id, GONE))
        return set(rows.scalars().all())

    async def home_page_id(self, db: AsyncSession, site_id: str) -> str | None:
        return (
            await db.execute(
                select(SitePage.id)
                .where(
                    SitePage.site_id == site_id,
                    func.regexp_replace(SitePage.url, "^https?://[^/]+", "").in_(("", "/")),
                )
                .order_by(func.length(SitePage.url))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def normalised_urls(self, db: AsyncSession, site_id: str) -> set[str]:
        rows = await db.execute(select(STRIPPED_URL).where(SitePage.site_id == site_id))
        return set(rows.scalars().all())

    async def link_targets(self, db: AsyncSession, site_id: str) -> dict[str, tuple[str, bool]]:
        rows = (
            await db.execute(
                text(
                    """
    select regexp_replace(t.url, '/+$', '') as key, t.id,
           (t.status between 200 and 299
            and not t.blocked_by_robots
            and coalesce(t.robots_directives, '') not ilike '%noindex%'
            and coalesce(t.x_robots_tag, '') not ilike '%noindex%'
            and (t.canonical is null
                 or regexp_replace(t.canonical, '/+$', '') = regexp_replace(t.url, '/+$', ''))
            and t.redirect_to is null) as canonical
      from site_pages t
     where t.site_id = :site_id
    """
                ),
                {"site_id": site_id},
            )
        ).mappings()
        return {str(r["key"]): (str(r["id"]), bool(r["canonical"])) for r in rows}

    async def changed_at_by_id(self, db: AsyncSession, site_id: str) -> dict[str, datetime]:
        rows = await db.execute(
            select(
                SitePage.id, func.coalesce(SitePage.content_changed_at, SitePage.created_at)
            ).where(SitePage.site_id == site_id)
        )
        return {r[0]: r[1] for r in rows}

    async def count(self, db: AsyncSession, site_id: str) -> int:
        n = (
            await db.execute(
                select(func.count()).select_from(SitePage).where(SitePage.site_id == site_id)
            )
        ).scalar_one()
        return int(n)

    async def extractable_hashes(self, db: AsyncSession, site_id: str) -> list[tuple[str, str]]:
        rows = await db.execute(
            select(SitePage.id, SitePage.content_hash)
            .where(SitePage.site_id == site_id, EXTRACTABLE)
            .order_by(SitePage.seq.asc())
        )
        return [(r.id, r.content_hash) for r in rows]

    async def extractable_hashes_by_site_ids(
        self, db: AsyncSession, site_ids: list[str]
    ) -> dict[str, dict[str, str]]:
        if not site_ids:
            return {}
        rows = await db.execute(
            select(SitePage.site_id, SitePage.id, SitePage.content_hash)
            .where(SitePage.site_id.in_(set(site_ids)), EXTRACTABLE)
            .order_by(SitePage.seq.asc())
        )
        found: dict[str, dict[str, str]] = {}
        for r in rows:
            found.setdefault(r.site_id, {})[r.id] = r.content_hash
        return found

    async def pending_records_by_ids(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> list[PendingPageRecord]:
        if not ids:
            return []
        rows = await db.execute(
            select(SitePage)
            .where(SitePage.site_id == site_id, SitePage.id.in_(set(ids)))
            .order_by(SitePage.seq.asc())
        )
        return [PendingPageRecord.model_validate(p) for p in rows.scalars()]

    async def list_render_eligible(
        self, db: AsyncSession, site_id: str, url: str | None = None
    ) -> list[RenderEligiblePage]:
        conds: list[Any] = [SitePage.site_id == site_id, RENDER_ELIGIBLE]
        if url is not None:
            conds.append(SitePage.url == url)
        rows = await db.execute(
            select(
                SitePage.id,
                SitePage.url,
                SitePage.content_hash,
                SitePage.depth,
                SitePage.inlinks,
                SitePage.seq,
            )
            .where(*conds)
            .order_by(SitePage.seq.asc())
        )
        return [RenderEligiblePage.model_validate(dict(r)) for r in rows.mappings()]

    async def crawl_known_pages(
        self, db: AsyncSession, site_id: str, limit: int = 20_000
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

    async def mark_all_unvisited(self, db: AsyncSession, site_id: str) -> int:
        result = await db.execute(
            update(SitePage)
            .where(SitePage.site_id == site_id)
            .values(visited=False)
            .returning(SitePage.id)
        )
        return len(result.scalars().all())

    async def mark_visited(self, db: AsyncSession, site_id: str, urls: list[str]) -> int:
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

    async def delete_unvisited(self, db: AsyncSession, site_id: str) -> int:
        result = await db.execute(
            delete(SitePage)
            .where(SitePage.site_id == site_id, SitePage.visited.is_(False))
            .returning(SitePage.id)
        )
        return len(result.scalars().all())

    async def insert(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> SitePageRecord:
        now = datetime.now(UTC)
        page = SitePage(
            **values,
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            created_at=now,
            updated_at=now,
        )
        db.add(page)
        await db.flush()
        await db.refresh(page)
        return SitePageRecord.model_validate(page)

    async def update(
        self, db: AsyncSession, site_id: str, page_id: str, values: dict[str, Any]
    ) -> SitePageRecord | None:
        page = await self._load(db, site_id, page_id=page_id)
        if page is None:
            return None
        for key, value in values.items():
            setattr(page, key, value)
        page.updated_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(page)
        return SitePageRecord.model_validate(page)

    async def delete(self, db: AsyncSession, site_id: str, page_id: str) -> SitePageRef | None:
        page = await self._load(db, site_id, page_id=page_id)
        if page is None:
            return None
        removed = SitePageRef(id=page.id, url=page.url)
        await db.delete(page)
        await db.flush()
        return removed

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[SitePageCrawlItem]
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
            row.update(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                created_at=now,
                updated_at=now,
            )
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

    async def write_graph_stamps(
        self, db: AsyncSession, site_id: str, stamps: dict[str, tuple[int, int | None]]
    ) -> None:
        now = datetime.now(UTC)
        await db.execute(
            update(SitePage)
            .where(SitePage.site_id == site_id)
            .values(inlinks=0, depth=None, updated_at=now)
        )
        rows = [
            {"id": page_id, "inlinks": inlinks, "depth": depth, "updated_at": now}
            for page_id, (inlinks, depth) in stamps.items()
        ]
        for start in range(0, len(rows), WRITE_BATCH):
            await db.execute(update(SitePage), rows[start : start + WRITE_BATCH])
        await db.flush()

    async def write_scores(
        self, db: AsyncSession, site_id: str, column: str, scores: dict[str, float]
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
        for start in range(0, len(entries), WRITE_BATCH):
            chunk = entries[start : start + WRITE_BATCH]
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
        self, db: AsyncSession, site_id: str, sitemap_urls: list[str]
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

    async def list_needing_chunks(self, db: AsyncSession, limit: int) -> list[SitePageChunkSource]:
        rows = await db.execute(
            select(*CHUNK_SOURCE_COLUMNS)
            .where(
                SitePage.status == 200,
                SitePage.body_text.is_not(None),
                SitePage.content_hash.is_not(None),
                SitePage.chunked_from_hash.is_distinct_from(SitePage.content_hash),
            )
            .order_by(SitePage.updated_at.asc())
            .limit(limit)
        )
        return [SitePageChunkSource.model_validate(dict(r)) for r in rows.mappings()]

    async def mark_chunked(
        self, db: AsyncSession, page_id: str, chunked_from_hash: str | None
    ) -> None:
        await db.execute(
            update(SitePage)
            .where(SitePage.id == page_id)
            .values(
                chunked_from_hash=chunked_from_hash,
                embed_state=None,
                embed_error=None,
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def unserved_page_ids(self, db: AsyncSession) -> list[str]:
        rows = await db.execute(select(SitePage.id).where(SitePage.status.is_distinct_from(200)))
        return list(rows.scalars().all())

    async def clear_chunked_hash(self, db: AsyncSession, page_ids: list[str]) -> int:
        if not page_ids:
            return 0
        result = await db.execute(
            update(SitePage)
            .where(SitePage.id.in_(set(page_ids)), SitePage.chunked_from_hash.is_not(None))
            .values(chunked_from_hash=None, updated_at=datetime.now(UTC))
            .returning(SitePage.id)
        )
        return len(result.scalars().all())

    async def mark_embed_failed(self, db: AsyncSession, page_id: str, message: str) -> None:
        await db.execute(
            update(SitePage)
            .where(SitePage.id == page_id)
            .values(embed_state="failed", embed_error=message, updated_at=datetime.now(UTC))
        )
        await db.flush()

    async def clear_embed_state(self, db: AsyncSession, page_ids: list[str]) -> int:
        if not page_ids:
            return 0
        result = await db.execute(
            update(SitePage)
            .where(SitePage.id.in_(set(page_ids)), SitePage.embed_state.is_not(None))
            .values(embed_state=None, embed_error=None, updated_at=datetime.now(UTC))
            .returning(SitePage.id)
        )
        return len(result.scalars().all())

    async def page_counts(self, db: AsyncSession, site_id: str) -> SitePageCountsRecord:
        row = (
            (
                await db.execute(
                    select(
                        self._count_if(~SitePage.blocked_by_robots).label("pages"),
                        self._count_if(SitePage.blocked_by_robots).label("blockedByRobots"),
                        self._count_if(
                            and_(
                                SitePage.blocked_by_robots,
                                or_(SitePage.in_sitemap, SitePage.inlinks > 0),
                            )
                        ).label("blockedAndDiscoverable"),
                        self._count_if(SitePage.status == 200).label("ok"),
                        self._count_if(
                            and_(
                                or_(SitePage.status >= 400, SitePage.status == 0),
                                SitePage.status.not_in((404, 410)),
                            )
                        ).label("errored"),
                        self._count_if(SitePage.status.in_((404, 410))).label("gone"),
                        self._count_if(and_(~SitePage.in_sitemap, SitePage.status == 200)).label(
                            "notInSitemap"
                        ),
                        self._count_if(
                            and_(SitePage.in_sitemap, SitePage.status.in_((404, 410)))
                        ).label("sitemapMissing"),
                        self._count_if(SitePage.status == 404).label("notFound"),
                        self._count_if(SitePage.status.in_((401, 403, 429))).label("blocked"),
                        self._count_if(SitePage.status >= 500).label("serverError"),
                        self._count_if(SitePage.status == 0).label("unreachable"),
                        self._count_if(
                            and_(
                                SitePage.in_sitemap,
                                SitePage.inlinks == 0,
                                SitePage.status == 200,
                            )
                        ).label("orphans"),
                        self._count_if(SitePage.shallow).label("shallow"),
                        self._count_if(SitePage.embed_state == "failed").label("embedFailed"),
                        self._count_if(text(f"({CRAWL_COMPLETE_SQL})")).label("crawlComplete"),
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

        by_shallow_reason = (
            await db.execute(
                select(SitePage.shallow_reason, cast(func.count(), Integer).label("n"))
                .where(SitePage.site_id == site_id, SitePage.shallow.is_(True))
                .group_by(SitePage.shallow_reason)
            )
        ).mappings()

        return SitePageCountsRecord(
            **dict(row),
            by_stage=[StageCount(stage=r["stage"], n=r["n"]) for r in by_stage],
            by_shallow_reason=[
                ShallowReasonCount(reason=r["shallow_reason"], n=r["n"]) for r in by_shallow_reason
            ],
        )

    async def page_discovery(
        self, db: AsyncSession, site_id: str, deep_from: int, cap: int
    ) -> SitePageDiscoveryRecord:
        deep = and_(LIVE, SitePage.depth >= deep_from)
        row = (
            (
                await db.execute(
                    select(
                        self._count_if(LIVE).label("live"),
                        self._count_if(and_(LIVE, SitePage.depth == 0)).label("home"),
                        self._count_if(ORPHAN).label("orphans"),
                        self._count_if(UNREACHABLE).label("unreachable"),
                        self._count_if(deep).label("deep"),
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
            orphan_pages=await self._discovery_pages(
                db, site_id, ORPHAN, [SitePage.in_sitemap.desc(), SitePage.url.asc()], cap
            ),
            unreachable_pages=await self._discovery_pages(
                db, site_id, UNREACHABLE, [SitePage.inlinks.asc(), SitePage.url.asc()], cap
            ),
            deep_pages=await self._discovery_pages(
                db,
                site_id,
                deep,
                [SitePage.depth.desc(), SitePage.inlinks.asc(), SitePage.url.asc()],
                cap,
            ),
        )

    async def _discovery_pages(
        self, db: AsyncSession, site_id: str, cond: Any, order: list[Any], cap: int
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

    async def _briefs(
        self, db: AsyncSession, conds: list[Any], body_chars: int | None = None
    ) -> list[SitePageBrief]:
        cols: list[Any] = list(BRIEF_COLUMNS)
        if body_chars is not None:
            cols.append(func.left(SitePage.body_text, body_chars).label("body_text"))
        rows = await db.execute(select(*cols).where(*conds).order_by(SitePage.seq.asc()))
        return [SitePageBrief.model_validate(dict(r)) for r in rows.mappings()]

    async def _load(
        self,
        db: AsyncSession,
        site_id: str,
        page_id: str | None = None,
        url: str | None = None,
    ) -> SitePage | None:
        match = SitePage.id == page_id if page_id else SitePage.url == url
        result = await db.execute(
            select(SitePage).where(SitePage.site_id == site_id, match).limit(1)
        )
        return result.scalars().first()

    def _record(self, page: SitePage | None) -> SitePageRecord | None:
        return None if page is None else SitePageRecord.model_validate(page)

    def _count_if(self, cond: Any) -> Any:
        return cast(func.count().filter(cond), Integer)

    def _order_by(self, specs: list[tuple[str, str | None]] | None, match_ids: list[str] | None):
        if not specs:
            if match_ids:
                return [
                    func.array_position(literal(list(match_ids), type_=ARRAY(TEXT)), SitePage.id)
                ]
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

    def _conditions(
        self,
        site_id: str,
        f: SitePageFilters,
        match_ids: list[str] | None = None,
        page_ids: list[str] | None = None,
    ):
        where = [SitePage.site_id == site_id]
        if f.url:
            where.append(SitePage.url == f.url)
        if f.urls:
            where.append(SitePage.url.in_(f.urls))
        if f.ids:
            where.append(SitePage.id.in_(f.ids))
        if match_ids:
            where.append(SitePage.id.in_(match_ids))
        if page_ids is not None:
            where.append(SitePage.id.in_(page_ids))
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


site_pages = SitePageRepository()
