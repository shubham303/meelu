from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_traffic.repositories.base import TrafficDailyRepository, day_value, page_bounds
from src.site_traffic.schemas import TrafficContentPageRow, TrafficContentPagesResult

PAGE_PATH_ORDERS = {
    "delta": "abs(cur.views - coalesce(prev.views, 0)) desc",
    "users": "cur.users desc",
    "keyEvents": "cur.key_events desc",
    "views": "cur.views desc",
}


class SiteTrafficPagesDailyRepository(TrafficDailyRepository):
    REPORT = "pages"

    async def by_page_path(
        self,
        db: AsyncSession,
        site_id: str,
        last_day: str,
        days: int,
        search: str | None = None,
        sort: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficContentPagesResult:
        limit, offset = page_bounds(limit, offset)
        search_filter = "and page_path ilike :search" if search else ""
        order = PAGE_PATH_ORDERS.get(sort or "views", PAGE_PATH_ORDERS["views"])
        params: dict[str, Any] = {
            "site_id": site_id,
            "last_day": day_value(last_day),
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
                      select page_path,
                             sum(views)::bigint as views,
                             sum(users)::bigint as users,
                             sum(engagement_seconds)::double precision as engagement_seconds,
                             sum(key_events)::double precision as key_events
                        from site_traffic_pages_daily
                       where site_id = :site_id and day > :last_day - :span and day <= :last_day {search_filter}
                       group by page_path
                    ),
                    prev as (
                      select page_path, sum(views)::bigint as views
                        from site_traffic_pages_daily
                       where site_id = :site_id
                         and day > :last_day - :span2
                         and day <= :last_day - :span
                         {search_filter}
                       group by page_path
                    )
                    select cur.*, coalesce(prev.views, 0)::bigint as prev_views, count(*) over ()::int as total
                      from cur
                      left join prev using (page_path)
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

        return TrafficContentPagesResult(
            total=int(rows[0]["total"]) if rows else 0,
            rows=[
                TrafficContentPageRow(
                    page_path=str(r["page_path"]),
                    views=int(r["views"] or 0),
                    prev_views=int(r["prev_views"] or 0),
                    users=int(r["users"] or 0),
                    engagement_seconds=float(r["engagement_seconds"] or 0),
                    key_events=float(r["key_events"] or 0),
                )
                for r in rows
            ],
        )


site_traffic_pages_dailies = SiteTrafficPagesDailyRepository()
