import re
from datetime import date
from typing import Any

from sqlalchemy import bindparam, delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_search.models.site_search_daily import SiteSearchDaily
from src.seo.site_search.schemas import (
    QueryWindowTotals,
    SearchCoverageRecord,
    SearchDailyRowInput,
    SearchMover,
    SearchMovers,
    SearchQueryRollup,
    SearchQueryRollupRow,
    SearchTotals,
)

WINDOW_DAYS = 28
YEAR_DAYS = 365
NORMALIZE_QUERY = r"lower(regexp_replace(btrim(query), '\s+', ' ', 'g'))"

INSERT_CHUNK = 1000

PAGE_SORTS = {
    "clicks": "cur.clicks",
    "delta": "abs(cur.clicks - coalesce(prev.clicks, 0))",
    "impressions": "cur.impressions",
    "ctr": "cur.clicks::float / nullif(cur.impressions, 0)",
    "position": "cur.position",
    "page": "cur.page",
}


def strip_slash(value: str) -> str:
    return re.sub(r"/+$", "", value)


def _day(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


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


def _weekly_series(by_weeks_back: dict[str, Any] | None, weeks: int = 8) -> list[int]:
    series = [0] * weeks
    for back, clicks in (by_weeks_back or {}).items():
        idx = weeks - 1 - int(back)
        if 0 <= idx < weeks:
            series[idx] = int(clicks)
    return series


class SiteSearchDailyRepository:
    async def replace_day(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        day: str,
        rows: list[SearchDailyRowInput],
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
                    "device": r.device,
                    "country": r.country,
                    "clicks": r.clicks,
                    "impressions": r.impressions,
                    "position": r.position,
                }
                for r in rows[i : i + INSERT_CHUNK]
            ]
            if chunk:
                await db.execute(insert(SiteSearchDaily), chunk)
        return len(rows)

    async def coverage(self, db: AsyncSession, site_id: str) -> SearchCoverageRecord:
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

    async def queries_rollup(
        self,
        db: AsyncSession,
        site_id: str,
        last_day: str,
        days: int,
        view: str | None = None,
        page: str | None = None,
        pages: list[str] | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SearchQueryRollup:
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
                   count(*) over ()::int as total
              from cur
              left join prev on prev.query = cur.query
              left join owner o on o.query = cur.query
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
                    page_id=None,
                    inlinks=None,
                    clicks=int(r["clicks"]),
                    prev_clicks=int(r["prev_clicks"]),
                    impressions=int(r["impressions"]),
                    position=float(r["position"]) if r["position"] is not None else None,
                    prev_position=float(r["prev_position"])
                    if r["prev_position"] is not None
                    else None,
                )
                for r in rows
            ],
        )

    async def movers(
        self, db: AsyncSession, site_id: str, last_day: str, days: int, limit: int = 10
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

    async def monthly_positions(
        self, db: AsyncSession, site_id: str, queries: list[str], country: str, since: date
    ) -> list[tuple[str, date, float, str]]:
        if not queries:
            return []
        stmt = text(
            f"""
            with by_page as (
              select {NORMALIZE_QUERY} as q,
                     date_trunc('month', day)::date as month,
                     page,
                     sum(impressions) as impressions,
                     sum(position * impressions) as weighted
                from site_search_daily
               where site_id = :site_id
                 and country = :country
                 and day >= :since
                 and {NORMALIZE_QUERY} in :queries
               group by 1, 2, 3
            )
            select q, month,
                   sum(weighted) / sum(impressions) as position,
                   (array_agg(page order by impressions desc))[1] as page
              from by_page
             group by q, month
            having sum(impressions) > 0
            """
        ).bindparams(bindparam("queries", expanding=True))
        rows = (
            await db.execute(
                stmt,
                {"site_id": site_id, "country": country, "since": since, "queries": queries},
            )
        ).all()
        return [(str(q), month, float(position), str(page)) for q, month, position, page in rows]

    async def queries_with_impressions(self, db: AsyncSession, site_id: str, days: int) -> set[str]:
        rows = await db.execute(
            text(
                f"""
                select distinct {NORMALIZE_QUERY} as q
                  from site_search_daily
                 where site_id = :site_id and day > current_date - :days and impressions > 0
                """
            ),
            {"site_id": site_id, "days": days},
        )
        return {str(q) for q in rows.scalars()}

    async def query_window_totals(self, db: AsyncSession, site_id: str) -> list[QueryWindowTotals]:
        rows = (
            (
                await db.execute(
                    text(
                        f"""
                    select {NORMALIZE_QUERY} as q,
                           sum(impressions) filter (where day > current_date - {WINDOW_DAYS}) as i28,
                           sum(clicks) filter (where day > current_date - {WINDOW_DAYS}) as c28,
                           sum(impressions) filter (where day > current_date - {2 * WINDOW_DAYS}
                                                      and day <= current_date - {WINDOW_DAYS}) as ip,
                           sum(clicks) filter (where day > current_date - {2 * WINDOW_DAYS}
                                                 and day <= current_date - {WINDOW_DAYS}) as cp,
                           sum(impressions) filter (where day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                                                      and day <= current_date - {YEAR_DAYS}) as ily,
                           sum(clicks) filter (where day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                                                 and day <= current_date - {YEAR_DAYS}) as cly
                      from site_search_daily
                     where site_id = :site_id and day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                     group by 1
                    """
                    ),
                    {"site_id": site_id},
                )
            )
            .mappings()
            .all()
        )
        return [
            QueryWindowTotals(
                query=str(r["q"]),
                impressions_28d=int(r["i28"] or 0),
                clicks_28d=int(r["c28"] or 0),
                impressions_prev_28d=int(r["ip"] or 0),
                clicks_prev_28d=int(r["cp"] or 0),
                impressions_ly_28d=int(r["ily"] or 0),
                clicks_ly_28d=int(r["cly"] or 0),
            )
            for r in rows
        ]


site_search_dailies = SiteSearchDailyRepository()
