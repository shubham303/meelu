import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import bindparam, delete, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.site_search.models.site_search_daily import SiteSearchDaily
from src.site_search.models.site_search_sync import SiteSearchSync
from src.site_search.schemas import (
    GooglePreferredCanonical,
    IndexationSummary,
    SearchCoverageRecord,
    SearchDailyPoint,
    SearchDailyRowInput,
    SearchInspectionInput,
    SearchMover,
    SearchMovers,
    SearchPageRollup,
    SearchPageRollupRow,
    SearchQueryRollup,
    SearchQueryRollupRow,
    SearchSyncRecord,
    SearchTotals,
)

INSERT_CHUNK = 1000

PAGE_SORTS = {
    "clicks": "cur.clicks",
    "delta": "abs(cur.clicks - coalesce(prev.clicks, 0))",
    "impressions": "cur.impressions",
    "ctr": "cur.clicks::float / nullif(cur.impressions, 0)",
    "position": "cur.position",
    "page": "cur.page",
    "index": "idx.index_state",
    "crawled": "idx.last_crawl_time",
    "inspected": "idx.index_checked_at",
}


def strip_slash(value: str) -> str:
    return re.sub(r"/+$", "", value)


def _day(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


async def replace_day(
    db: AsyncSession, user_id: str, site_id: str, day: str, rows: list[SearchDailyRowInput]
) -> int:
    await db.execute(
        delete(SiteSearchDaily).where(
            SiteSearchDaily.site_id == site_id, SiteSearchDaily.day == _day(day)
        )
    )
    for i in range(0, len(rows), INSERT_CHUNK):
        chunk = [
            {
                "id": uid("ssd"),
                "user_id": user_id,
                "site_id": site_id,
                "day": _day(day),
                "query": r.query,
                "page": r.page,
                "clicks": r.clicks,
                "impressions": r.impressions,
                "position": r.position,
            }
            for r in rows[i : i + INSERT_CHUNK]
        ]
        if chunk:
            await db.execute(insert(SiteSearchDaily), chunk)
    return len(rows)


async def coverage(db: AsyncSession, site_id: str) -> SearchCoverageRecord:
    row = (
        (
            await db.execute(
                text(
                    """
                select min(day)::text as first_day,
                       max(day)::text as last_day,
                       count(distinct day)::int as days_stored,
                       coalesce(sum(impressions) filter (where day > current_date - 31), 0)::bigint as recent
                  from site_search_daily
                 where site_id = :site_id
                """
                ),
                {"site_id": site_id},
            )
        )
        .mappings()
        .first()
    )
    return SearchCoverageRecord(
        first_day=row["first_day"] if row else None,
        last_day=row["last_day"] if row else None,
        days_stored=int(row["days_stored"] or 0) if row else 0,
        impressions_28d=int(row["recent"] or 0) if row else 0,
    )


async def indexation_counts(db: AsyncSession, site_id: str) -> IndexationSummary:
    judged = "p.site_id = :site_id and p.status between 200 and 299 and not p.blocked_by_robots"
    rows = (
        (
            await db.execute(
                text(
                    f"""
                select coalesce(idx.index_state, 'unchecked') as state, count(*)::int as n
                  from site_pages p
                  left join site_page_index_status idx on idx.page_id = p.id
                 where {judged}
                 group by 1
                """
                ),
                {"site_id": site_id},
            )
        )
        .mappings()
        .all()
    )
    prefers = (
        (
            await db.execute(
                text(
                    f"""
                select p.url, idx.google_canonical, idx.coverage_state
                  from site_pages p
                  join site_page_index_status idx on idx.page_id = p.id
                 where {judged}
                   and idx.google_canonical is not null and idx.google_canonical <> ''
                   and idx.google_canonical <> p.url
                 order by p.inlinks desc
                 limit 10
                """
                ),
                {"site_id": site_id},
            )
        )
        .mappings()
        .all()
    )

    counts = {r["state"]: int(r["n"]) for r in rows}
    return IndexationSummary(
        counts=counts,
        never_checked=counts.get("unchecked", 0),
        google_prefers=[
            GooglePreferredCanonical(
                url=r["url"],
                google_canonical=r["google_canonical"],
                coverage_state=r["coverage_state"],
            )
            for r in prefers
        ],
    )


def _totals_row(row: Any) -> SearchTotals:
    clicks = int(row["clicks"] or 0) if row else 0
    impressions = int(row["impressions"] or 0) if row else 0
    position = row["position"] if row else None
    return SearchTotals(
        clicks=clicks,
        impressions=impressions,
        ctr=clicks / impressions if impressions > 0 else None,
        position=float(position) if position is not None else None,
    )


def _pages_filter(pages: list[str] | None) -> str:
    if not pages:
        return ""
    return "and regexp_replace(page, '/+$', '') in :pages"


def _pages_params(pages: list[str] | None) -> dict[str, Any]:
    if not pages:
        return {}
    return {"pages": [strip_slash(p) for p in pages]}


def _bind_pages(stmt: Any, pages: list[str] | None) -> Any:
    if not pages:
        return stmt
    return stmt.bindparams(bindparam("pages", expanding=True))


async def totals_for_window(
    db: AsyncSession,
    site_id: str,
    last_day: str,
    days: int,
    offset_days: int = 0,
    pages: list[str] | None = None,
) -> SearchTotals:
    stmt = text(
        f"""
        select coalesce(sum(clicks), 0)::bigint as clicks,
               coalesce(sum(impressions), 0)::bigint as impressions,
               sum(position * impressions) / nullif(sum(impressions), 0) as position
          from site_search_daily
         where site_id = :site_id
           and day > :last_day - :span
           and day <= :last_day - :offset
           {_pages_filter(pages)}
        """
    )
    row = (
        (
            await db.execute(
                _bind_pages(stmt, pages),
                {
                    "site_id": site_id,
                    "last_day": _day(last_day),
                    "span": days + offset_days,
                    "offset": offset_days,
                    **_pages_params(pages),
                },
            )
        )
        .mappings()
        .first()
    )
    return _totals_row(row)


async def daily_series(
    db: AsyncSession,
    site_id: str,
    last_day: str,
    days: int,
    pages: list[str] | None = None,
) -> list[SearchDailyPoint]:
    by_page = bool(pages)
    page_col = "regexp_replace(page, '/+$', '') as page," if by_page else "null as page,"
    stmt = text(
        f"""
        select day::text as day,
               {page_col}
               sum(clicks)::bigint as clicks,
               sum(impressions)::bigint as impressions,
               sum(position * impressions) / nullif(sum(impressions), 0) as position
          from site_search_daily
         where site_id = :site_id
           and day > :last_day - :span
           and day <= :last_day
           {_pages_filter(pages)}
         group by 1{", 2" if by_page else ""}
         order by 1
        """
    )
    rows = (
        (
            await db.execute(
                _bind_pages(stmt, pages),
                {
                    "site_id": site_id,
                    "last_day": _day(last_day),
                    "span": days,
                    **_pages_params(pages),
                },
            )
        )
        .mappings()
        .all()
    )
    return [
        SearchDailyPoint(
            day=str(r["day"]),
            page=r["page"],
            clicks=int(r["clicks"]),
            impressions=int(r["impressions"]),
            position=float(r["position"]) if r["position"] is not None else None,
        )
        for r in rows
    ]


async def weekly_clicks(db: AsyncSession, site_id: str, last_day: str, weeks: int) -> list[int]:
    rows = (
        (
            await db.execute(
                text(
                    """
                select floor((:last_day - day) / 7)::int as weeks_back,
                       sum(clicks)::bigint as clicks
                  from site_search_daily
                 where site_id = :site_id and day > :last_day - :span
                 group by 1
                """
                ),
                {"site_id": site_id, "last_day": _day(last_day), "span": weeks * 7},
            )
        )
        .mappings()
        .all()
    )
    series = [0] * weeks
    for r in rows:
        idx = weeks - 1 - int(r["weeks_back"])
        if 0 <= idx < weeks:
            series[idx] = int(r["clicks"])
    return series


def _weekly_series(by_weeks_back: dict[str, Any] | None, weeks: int = 8) -> list[int]:
    series = [0] * weeks
    for back, clicks in (by_weeks_back or {}).items():
        idx = weeks - 1 - int(back)
        if 0 <= idx < weeks:
            series[idx] = int(clicks)
    return series


async def pages_rollup(
    db: AsyncSession,
    site_id: str,
    last_day: str,
    days: int,
    limit: int | None = None,
    offset: int | None = None,
    sort: str | None = None,
    dir: str | None = None,
    search: str | None = None,
) -> SearchPageRollup:
    limit = min(max(limit if limit is not None else 50, 1), 200)
    offset = max(offset if offset is not None else 0, 0)
    sort_expr = PAGE_SORTS.get(sort or "clicks", PAGE_SORTS["clicks"])
    direction = dir if dir is not None else ("asc" if sort == "page" else "desc")
    direction = "asc" if direction == "asc" else "desc"
    order = f"{sort_expr} {direction} nulls last, cur.clicks desc"
    search_filter = "and page ilike :search" if search else ""
    params: dict[str, Any] = {
        "site_id": site_id,
        "last_day": _day(last_day),
        "span": days,
        "span2": days * 2,
        "limit": limit,
        "offset": offset,
    }
    if search:
        params["search"] = f"%{search}%"

    rows = (
        (
            await db.execute(
                text(
                    f"""
                with cur as (
                  select page,
                         sum(clicks)::bigint as clicks,
                         sum(impressions)::bigint as impressions,
                         sum(position * impressions) / nullif(sum(impressions), 0) as position
                    from site_search_daily
                   where site_id = :site_id and day > :last_day - :span {search_filter}
                   group by page
                ),
                prev as (
                  select page,
                         sum(clicks)::bigint as clicks,
                         sum(position * impressions) / nullif(sum(impressions), 0) as position
                    from site_search_daily
                   where site_id = :site_id
                     and day > :last_day - :span2 and day <= :last_day - :span
                     {search_filter}
                   group by page
                ),
                top_query as (
                  select distinct on (page) page, query
                    from site_search_daily
                   where site_id = :site_id and day > :last_day - :span {search_filter}
                   group by page, query
                   order by page, sum(clicks) desc, sum(impressions) desc
                ),
                weekly as (
                  select page,
                         floor((:last_day - day) / 7)::int as weeks_back,
                         sum(clicks)::bigint as clicks
                    from site_search_daily
                   where site_id = :site_id and day > :last_day - 56
                   group by page, 2
                )
                select cur.page,
                       cur.clicks,
                       cur.impressions,
                       cur.position,
                       coalesce(prev.clicks, 0)::bigint as prev_clicks,
                       prev.position as prev_position,
                       tq.query as top_query,
                       p.id as page_id,
                       p.title,
                       p.inlinks,
                       idx.index_state,
                       idx.coverage_state,
                       idx.google_canonical,
                       idx.last_crawl_time::text as last_crawl_time,
                       idx.index_checked_at::text as index_checked_at,
                       coalesce(
                         (select jsonb_object_agg(w.weeks_back, w.clicks) from weekly w where w.page = cur.page),
                         '{{}}'::jsonb
                       ) as weekly,
                       count(*) over ()::int as total
                  from cur
                  left join prev on prev.page = cur.page
                  left join top_query tq on tq.page = cur.page
                  left join site_pages p
                    on p.site_id = :site_id
                   and regexp_replace(p.url, '/+$', '') = regexp_replace(cur.page, '/+$', '')
                  left join site_page_index_status idx on idx.page_id = p.id
                 order by {order}
                 limit :limit offset :offset
                """
                ),
                params,
            )
        )
        .mappings()
        .all()
    )

    total = int(rows[0]["total"]) if rows else 0
    return SearchPageRollup(
        total=total,
        rows=[
            SearchPageRollupRow(
                page=str(r["page"]),
                page_id=r["page_id"],
                title=r["title"],
                inlinks=int(r["inlinks"]) if r["inlinks"] is not None else None,
                index_state=r["index_state"],
                coverage_state=r["coverage_state"],
                google_canonical=r["google_canonical"],
                last_crawl_time=r["last_crawl_time"],
                index_checked_at=r["index_checked_at"],
                top_query=r["top_query"],
                clicks=int(r["clicks"]),
                prev_clicks=int(r["prev_clicks"]),
                impressions=int(r["impressions"]),
                position=float(r["position"]) if r["position"] is not None else None,
                prev_position=float(r["prev_position"]) if r["prev_position"] is not None else None,
                weekly=_weekly_series(r["weekly"]),
            )
            for r in rows
        ],
    )


async def queries_rollup(
    db: AsyncSession,
    site_id: str,
    last_day: str,
    days: int,
    view: str | None = None,
    page: str | None = None,
    pages: list[str] | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> SearchQueryRollup:
    limit = min(max(limit if limit is not None else 50, 1), 200)
    offset = max(offset if offset is not None else 0, 0)
    striking = view == "striking"

    filters = ["true"]
    if striking:
        filters.append("cur.position >= 8 and cur.position <= 15 and cur.impressions >= 50")
    if search:
        filters.append("cur.query ilike :search")

    params: dict[str, Any] = {
        "site_id": site_id,
        "last_day": _day(last_day),
        "span": days,
        "span2": days * 2,
        "limit": limit,
        "offset": offset,
    }
    if search:
        params["search"] = f"%{search}%"

    if page:
        page_filter = "and regexp_replace(page, '/+$', '') = :page"
        params["page"] = strip_slash(page)
        scoped_pages = None
    else:
        page_filter = _pages_filter(pages)
        params.update(_pages_params(pages))
        scoped_pages = pages

    stmt = text(
        f"""
        with cur as (
          select query,
                 sum(clicks)::bigint as clicks,
                 sum(impressions)::bigint as impressions,
                 sum(position * impressions) / nullif(sum(impressions), 0) as position
            from site_search_daily
           where site_id = :site_id and day > :last_day - :span {page_filter}
           group by query
        ),
        prev as (
          select query,
                 sum(clicks)::bigint as clicks,
                 sum(position * impressions) / nullif(sum(impressions), 0) as position
            from site_search_daily
           where site_id = :site_id
             and day > :last_day - :span2 and day <= :last_day - :span
             {page_filter}
           group by query
        ),
        owner as (
          select distinct on (query) query, page
            from site_search_daily
           where site_id = :site_id and day > :last_day - :span {page_filter}
           group by query, page
           order by query, sum(impressions) desc
        )
        select cur.query,
               cur.clicks,
               cur.impressions,
               cur.position,
               coalesce(prev.clicks, 0)::bigint as prev_clicks,
               prev.position as prev_position,
               o.page,
               p.id as page_id,
               p.inlinks,
               count(*) over ()::int as total
          from cur
          left join prev on prev.query = cur.query
          left join owner o on o.query = cur.query
          left join site_pages p
            on p.site_id = :site_id
           and regexp_replace(p.url, '/+$', '') = regexp_replace(o.page, '/+$', '')
         where {" and ".join(filters)}
         order by {"cur.impressions desc" if striking else "cur.clicks desc"}
         limit :limit offset :offset
        """
    )
    rows = (await db.execute(_bind_pages(stmt, scoped_pages), params)).mappings().all()

    total = int(rows[0]["total"]) if rows else 0
    return SearchQueryRollup(
        total=total,
        rows=[
            SearchQueryRollupRow(
                query=str(r["query"]),
                page=r["page"],
                page_id=r["page_id"],
                inlinks=int(r["inlinks"]) if r["inlinks"] is not None else None,
                clicks=int(r["clicks"]),
                prev_clicks=int(r["prev_clicks"]),
                impressions=int(r["impressions"]),
                position=float(r["position"]) if r["position"] is not None else None,
                prev_position=float(r["prev_position"]) if r["prev_position"] is not None else None,
            )
            for r in rows
        ],
    )


async def movers(
    db: AsyncSession, site_id: str, last_day: str, days: int, limit: int = 10
) -> SearchMovers:
    rows = (
        (
            await db.execute(
                text(
                    """
                with both_windows as (
                  select kind, key,
                         sum(clicks) filter (where recent)::bigint as clicks,
                         sum(clicks) filter (where not recent)::bigint as prev_clicks,
                         sum(position * impressions) filter (where recent)
                           / nullif(sum(impressions) filter (where recent), 0) as position,
                         sum(position * impressions) filter (where not recent)
                           / nullif(sum(impressions) filter (where not recent), 0) as prev_position
                    from (
                      select unnest(array['page', 'query']) as kind,
                             unnest(array[page, query]) as key,
                             clicks, impressions, position,
                             day > :last_day - :span as recent
                        from site_search_daily
                       where site_id = :site_id and day > :last_day - :span2
                    ) expanded
                   group by kind, key
                )
                select *, coalesce(clicks, 0) - coalesce(prev_clicks, 0) as delta
                  from both_windows
                 where abs(coalesce(clicks, 0) - coalesce(prev_clicks, 0)) >= 3
                 order by abs(coalesce(clicks, 0) - coalesce(prev_clicks, 0)) desc
                 limit :limit
                """
                ),
                {
                    "site_id": site_id,
                    "last_day": _day(last_day),
                    "span": days,
                    "span2": days * 2,
                    "limit": limit * 4,
                },
            )
        )
        .mappings()
        .all()
    )

    movers_all = [
        SearchMover(
            kind=r["kind"],
            key=str(r["key"]),
            clicks=int(r["clicks"] or 0),
            prev_clicks=int(r["prev_clicks"] or 0),
            position=float(r["position"]) if r["position"] is not None else None,
            prev_position=float(r["prev_position"]) if r["prev_position"] is not None else None,
        )
        for r in rows
    ]
    return SearchMovers(
        up=[m for m in movers_all if m.clicks > m.prev_clicks][:limit],
        down=[m for m in movers_all if m.clicks < m.prev_clicks][:limit],
    )


def _sync_record(row: SiteSearchSync | None) -> SearchSyncRecord | None:
    return None if row is None else SearchSyncRecord.model_validate(row)


async def open_sync(
    db: AsyncSession, user_id: str, site_id: str, trigger: str
) -> SearchSyncRecord | None:
    stmt = (
        pg_insert(SiteSearchSync)
        .values(id=uid("ssync"), user_id=user_id, site_id=site_id, trigger=trigger, status="queued")
        .on_conflict_do_nothing()
        .returning(SiteSearchSync)
    )
    return _sync_record((await db.execute(stmt)).scalars().first())


async def active_sync(db: AsyncSession, site_id: str) -> SearchSyncRecord | None:
    result = await db.execute(
        select(SiteSearchSync)
        .where(SiteSearchSync.site_id == site_id, SiteSearchSync.status.in_(["queued", "running"]))
        .limit(1)
    )
    return _sync_record(result.scalars().first())


async def get_sync(db: AsyncSession, site_id: str, id: str) -> SearchSyncRecord | None:
    result = await db.execute(
        select(SiteSearchSync)
        .where(SiteSearchSync.site_id == site_id, SiteSearchSync.id == id)
        .limit(1)
    )
    return _sync_record(result.scalars().first())


async def latest_sync(db: AsyncSession, site_id: str) -> SearchSyncRecord | None:
    result = await db.execute(
        select(SiteSearchSync)
        .where(SiteSearchSync.site_id == site_id)
        .order_by(SiteSearchSync.seq.desc())
        .limit(1)
    )
    return _sync_record(result.scalars().first())


async def patch_sync(
    db: AsyncSession, site_id: str, id: str, patch: dict[str, Any]
) -> SearchSyncRecord | None:
    values = dict(patch)
    for key in ("first_day", "last_day"):
        if isinstance(values.get(key), str):
            values[key] = date.fromisoformat(values[key])
    values["updated_at"] = datetime.now(UTC)
    stmt = (
        update(SiteSearchSync)
        .where(SiteSearchSync.site_id == site_id, SiteSearchSync.id == id)
        .values(**values)
        .returning(SiteSearchSync)
    )
    return _sync_record((await db.execute(stmt)).scalars().first())


async def reap_stalled_syncs(db: AsyncSession, site_id: str, stale_ms: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(milliseconds=stale_ms)
    now = datetime.now(UTC)
    stmt = (
        update(SiteSearchSync)
        .where(
            SiteSearchSync.site_id == site_id,
            SiteSearchSync.status.in_(["queued", "running"]),
            text("coalesce(heartbeat_at, created_at) < :cutoff").bindparams(cutoff=cutoff),
        )
        .values(
            status="failed",
            error="the process running it stopped reporting",
            finished_at=now,
            updated_at=now,
        )
        .returning(SiteSearchSync.id)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return len(rows)


EXCLUDED_HINTS = (
    "noindex",
    "duplicate",
    "alternate",
    "canonical",
    "redirect",
    "excluded",
    "not found",
    "soft 404",
)


def classify_coverage(verdict: str | None, coverage_state: str | None) -> str:
    state = (coverage_state or "").lower()
    if verdict == "PASS":
        return "indexed"
    if "crawled" in state and "not indexed" in state:
        return "crawled-not-indexed"
    if "discovered" in state:
        return "discovered"
    if "unknown to google" in state:
        return "unknown-to-google"
    if "blocked" in state or "robots" in state:
        return "blocked"
    if any(hint in state for hint in EXCLUDED_HINTS):
        return "excluded"
    return "unknown"


async def apply_inspections(
    db: AsyncSession, site_id: str, rows: list[SearchInspectionInput]
) -> int:
    deduped = list({strip_slash(r.url): r for r in rows}.values())
    applied = 0
    for i in range(0, len(deduped), 200):
        chunk = deduped[i : i + 200]
        values_sql = []
        params: dict[str, Any] = {"site_id": site_id}
        for n, r in enumerate(chunk):
            values_sql.append(f"(:id{n}, :url{n}, :state{n}, :cov{n}, :canon{n}, :time{n})")
            params[f"id{n}"] = uid("pidx")
            params[f"url{n}"] = strip_slash(r.url)
            params[f"state{n}"] = classify_coverage(r.verdict, r.coverage_state)
            params[f"cov{n}"] = r.coverage_state
            params[f"canon{n}"] = r.google_canonical
            params[f"time{n}"] = r.last_crawl_time
        result = await db.execute(
            text(
                f"""
                insert into site_page_index_status
                  (id, user_id, site_id, page_id, index_state, coverage_state, google_canonical, last_crawl_time, index_checked_at)
                select v.id, p.user_id, p.site_id, p.id, v.index_state, v.coverage_state, v.google_canonical,
                       v.last_crawl_time::timestamptz, now()
                  from (values {", ".join(values_sql)}) as v(id, url, index_state, coverage_state, google_canonical, last_crawl_time)
                  join site_pages p on p.site_id = :site_id and regexp_replace(p.url, '/+$', '') = v.url
                on conflict (page_id) do update
                   set index_state = excluded.index_state,
                       coverage_state = excluded.coverage_state,
                       google_canonical = excluded.google_canonical,
                       last_crawl_time = excluded.last_crawl_time,
                       index_checked_at = now(),
                       updated_at = now()
                """
            ),
            params,
        )
        applied += result.rowcount if result.rowcount is not None else len(chunk)
    return applied


async def inspection_targets(db: AsyncSession, site_id: str, limit: int) -> list[str]:
    rows = (
        (
            await db.execute(
                text(
                    """
                select p.url
                  from site_pages p
                  left join site_page_index_status idx on idx.page_id = p.id
                 where p.site_id = :site_id
                   and p.status between 200 and 299
                   and not p.blocked_by_robots
                   and p.fetch_error is null
                   and (idx.index_checked_at is null or idx.index_checked_at < now() - interval '14 days')
                 order by idx.index_checked_at asc nulls first, p.inlinks desc
                 limit :limit
                """
                ),
                {"site_id": site_id, "limit": min(max(limit, 1), 1000)},
            )
        )
        .mappings()
        .all()
    )
    return [r["url"] for r in rows]
