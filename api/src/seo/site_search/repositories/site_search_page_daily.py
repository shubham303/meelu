from typing import Any

from sqlalchemy import bindparam, delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_search.models.site_search_page_daily import SiteSearchPageDaily
from src.seo.site_search.repositories.site_search_daily import (
    INSERT_CHUNK,
    PAGE_SORTS,
    WINDOW_DAYS,
    _bind_pages,
    _day,
    _pages_filter,
    _pages_params,
    _totals_row,
    _weekly_series,
    strip_slash,
)
from src.seo.site_search.schemas import (
    SearchDailyPoint,
    SearchPageRollup,
    SearchPageRollupRow,
    SearchPageRowInput,
    SearchTotals,
)


class SiteSearchPageDailyRepository:
    async def replace_day(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        day: str,
        rows: list[SearchPageRowInput],
        final: bool,
    ) -> int:
        await db.execute(
            delete(SiteSearchPageDaily).where(
                SiteSearchPageDaily.site_id == site_id, SiteSearchPageDaily.day == _day(day)
            )
        )
        by_page = list({r.page: r for r in rows}.values())
        for i in range(0, len(by_page), INSERT_CHUNK):
            await db.execute(
                insert(SiteSearchPageDaily),
                [
                    {
                        "id": uid("ssp"),
                        "user_id": user_id,
                        "site_id": site_id,
                        "day": _day(day),
                        "page": r.page,
                        "clicks": r.clicks,
                        "impressions": r.impressions,
                        "position": r.position,
                        "final": final,
                    }
                    for r in by_page[i : i + INSERT_CHUNK]
                ],
            )
        return len(by_page)

    async def totals_for_window(
        self,
        db: AsyncSession,
        site_id: str,
        last_day: str,
        days: int,
        offset_days: int,
        pages: list[str],
    ) -> SearchTotals:
        stmt = text(
            f"""
            select coalesce(sum(clicks), 0)::bigint as clicks,
                   coalesce(sum(impressions), 0)::bigint as impressions,
                   sum(position * impressions) / nullif(sum(impressions), 0) as position
              from site_search_page_daily
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
        self, db: AsyncSession, site_id: str, last_day: str, days: int, pages: list[str]
    ) -> list[SearchDailyPoint]:
        stmt = text(
            f"""
            select day::text as day,
                   regexp_replace(page, '/+$', '') as page,
                   sum(clicks)::bigint as clicks,
                   sum(impressions)::bigint as impressions,
                   sum(position * impressions) / nullif(sum(impressions), 0) as position
              from site_search_page_daily
             where site_id = :site_id
               and day > :last_day - :span
               and day <= :last_day
               {_pages_filter(pages)}
             group by 1, 2
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

    async def pages_rollup(
        self,
        db: AsyncSession,
        site_id: str,
        last_day: str,
        days: int,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort: str | None = None,
        dir: str = "desc",
    ) -> SearchPageRollup:
        sort_expr = PAGE_SORTS.get(sort or "clicks", PAGE_SORTS["clicks"])
        direction = "asc" if dir == "asc" else "desc"
        order = f"{sort_expr} {direction} nulls last, cur.clicks desc"
        search_filter = "and page ilike :search" if search else ""
        page_clause = "offset :offset" if limit is None else "limit :limit offset :offset"
        params: dict[str, Any] = {
            "site_id": site_id,
            "last_day": _day(last_day),
            "span": days,
            "span2": days * 2,
            "offset": offset,
        }
        if limit is not None:
            params["limit"] = limit
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
                        from site_search_page_daily
                       where site_id = :site_id
                         and day > :last_day - :span and day <= :last_day {search_filter}
                       group by page
                    ),
                    prev as (
                      select page,
                             sum(clicks)::bigint as clicks,
                             sum(position * impressions) / nullif(sum(impressions), 0) as position
                        from site_search_page_daily
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
                        from site_search_page_daily
                       where site_id = :site_id and day > :last_day - 56 and day <= :last_day
                       group by page, 2
                    )
                    select cur.page,
                           cur.clicks,
                           cur.impressions,
                           cur.position,
                           coalesce(prev.clicks, 0)::bigint as prev_clicks,
                           prev.position as prev_position,
                           tq.query as top_query,
                           coalesce(
                             (select jsonb_object_agg(w.weeks_back, w.clicks) from weekly w where w.page = cur.page),
                             '{{}}'::jsonb
                           ) as weekly,
                           count(*) over ()::int as total
                      from cur
                      left join prev on prev.page = cur.page
                      left join top_query tq on tq.page = cur.page
                     order by {order}
                     {page_clause}
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
                    page_id=None,
                    title=None,
                    inlinks=None,
                    index_state=None,
                    coverage_state=None,
                    google_canonical=None,
                    last_crawl_time=None,
                    index_checked_at=None,
                    top_query=r["top_query"],
                    clicks=int(r["clicks"]),
                    prev_clicks=int(r["prev_clicks"]),
                    impressions=int(r["impressions"]),
                    position=float(r["position"]) if r["position"] is not None else None,
                    prev_position=float(r["prev_position"])
                    if r["prev_position"] is not None
                    else None,
                    weekly=_weekly_series(r["weekly"]),
                )
                for r in rows
            ],
        )

    async def page_positions(
        self, db: AsyncSession, site_id: str, pages: list[str], days: int = WINDOW_DAYS
    ) -> dict[str, tuple[float, int]]:
        if not pages:
            return {}
        stmt = text(
            """
            select regexp_replace(page, '/+$', '') as page,
                   sum(position * impressions) / sum(impressions) as position,
                   sum(impressions) as impressions
              from site_search_page_daily
             where site_id = :site_id
               and regexp_replace(page, '/+$', '') in :pages
               and day > (select max(day) from site_search_page_daily where site_id = :site_id) - :days
             group by 1
            having sum(impressions) > 0
            """
        ).bindparams(bindparam("pages", expanding=True))
        rows = await db.execute(
            stmt,
            {
                "site_id": site_id,
                "pages": list({strip_slash(p) for p in pages}),
                "days": days,
            },
        )
        return {str(r.page): (float(r.position), int(r.impressions)) for r in rows}


site_search_pages = SiteSearchPageDailyRepository()
