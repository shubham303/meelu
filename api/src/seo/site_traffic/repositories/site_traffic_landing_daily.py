from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.site_traffic.repositories.base import TrafficDailyRepository, day_value, page_bounds
from src.seo.site_traffic.schemas import TrafficLandingPageRow, TrafficLandingPagesResult

LANDING_ORDERS = {
    "delta": "abs(cur.sessions - coalesce(prev.sessions, 0)) desc",
    "keyEvents": "cur.key_events desc",
    "revenue": "cur.revenue desc",
    "sessions": "cur.sessions desc",
}


class SiteTrafficLandingDailyRepository(TrafficDailyRepository):
    REPORT = "landing"

    async def by_landing_page(
        self,
        db: AsyncSession,
        site_id: str,
        last_day: str,
        days: int,
        channel: str | None = None,
        search: str | None = None,
        sort: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficLandingPagesResult:
        limit, offset = page_bounds(limit, offset)
        channel_filter = "and channel = :channel" if channel else ""
        search_filter = "and landing_page ilike :search" if search else ""
        order = LANDING_ORDERS.get(sort or "sessions", LANDING_ORDERS["sessions"])
        params: dict[str, Any] = {
            "site_id": site_id,
            "last_day": day_value(last_day),
            "span": days,
            "span2": days * 2,
            "limit": limit,
            "offset": offset,
        }
        if channel:
            params["channel"] = channel
        if search:
            params["search"] = f"%{search}%"

        rows = (
            (
                await db.execute(
                    text(
                        f"""
                    with cur as (
                      select landing_page,
                             sum(sessions)::bigint as sessions,
                             sum(engaged_sessions)::bigint as engaged_sessions,
                             sum(key_events)::double precision as key_events,
                             sum(revenue)::double precision as revenue
                        from site_traffic_landing_daily
                       where site_id = :site_id and day > :last_day - :span and day <= :last_day
                         {channel_filter} {search_filter}
                       group by landing_page
                    ),
                    prev as (
                      select landing_page,
                             sum(sessions)::bigint as sessions,
                             sum(key_events)::double precision as key_events,
                             sum(revenue)::double precision as revenue
                        from site_traffic_landing_daily
                       where site_id = :site_id
                         and day > :last_day - :span2
                         and day <= :last_day - :span
                         {channel_filter} {search_filter}
                       group by landing_page
                    )
                    select cur.landing_page,
                           cur.sessions,
                           cur.engaged_sessions,
                           cur.key_events,
                           cur.revenue,
                           coalesce(prev.sessions, 0)::bigint as prev_sessions,
                           coalesce(prev.key_events, 0)::double precision as prev_key_events,
                           coalesce(prev.revenue, 0)::double precision as prev_revenue,
                           count(*) over ()::int as total
                      from cur
                      left join prev on prev.landing_page = cur.landing_page
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

        return TrafficLandingPagesResult(
            total=int(rows[0]["total"]) if rows else 0,
            rows=[
                TrafficLandingPageRow(
                    landing_page=str(r["landing_page"]),
                    page_id=None,
                    url=None,
                    title=None,
                    sessions=int(r["sessions"] or 0),
                    prev_sessions=int(r["prev_sessions"] or 0),
                    engaged_sessions=int(r["engaged_sessions"] or 0),
                    key_events=float(r["key_events"] or 0),
                    prev_key_events=float(r["prev_key_events"] or 0),
                    revenue=float(r["revenue"] or 0),
                    prev_revenue=float(r["prev_revenue"] or 0),
                )
                for r in rows
            ],
        )

    async def sessions_by_path(self, db: AsyncSession, site_id: str, days: int) -> dict[str, int]:
        rows = (
            await db.execute(
                text(
                    """
                select landing_page as path, sum(sessions)::int as sessions
                  from site_traffic_landing_daily
                 where site_id = :site_id
                   and day >= current_date - :days
                 group by 1
                """
                ),
                {"site_id": site_id, "days": days},
            )
        ).mappings()
        return {str(r["path"]): int(r["sessions"] or 0) for r in rows}


site_traffic_landing_dailies = SiteTrafficLandingDailyRepository()
