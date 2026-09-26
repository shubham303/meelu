from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_traffic.repositories.base import (
    WINDOW_FILTER,
    TrafficDailyRepository,
    day_value,
    window_params,
)
from src.site_traffic.schemas import TrafficDayRange, TrafficSeriesPoint, TrafficTotals


class SiteTrafficTotalsDailyRepository(TrafficDailyRepository):
    REPORT = "totals"

    async def day_range(self, db: AsyncSession, site_id: str) -> TrafficDayRange:
        row = (
            (
                await db.execute(
                    text(
                        """
                    select min(day)::text as first_day,
                           max(day)::text as last_day,
                           count(distinct day)::int as days_stored,
                           coalesce(sum(sessions) filter (where day > current_date - 29), 0)::bigint as recent
                      from site_traffic_totals_daily
                     where site_id = :site_id
                    """
                    ),
                    {"site_id": site_id},
                )
            )
            .mappings()
            .first()
        )
        return TrafficDayRange(
            first_day=row["first_day"] if row else None,
            last_day=row["last_day"] if row else None,
            days_stored=int(row["days_stored"] or 0) if row else 0,
            sessions_28d=int(row["recent"] or 0) if row else 0,
        )

    async def totals(
        self, db: AsyncSession, site_id: str, last_day: str, days: int, offset_days: int = 0
    ) -> TrafficTotals:
        row = (
            (
                await db.execute(
                    text(
                        f"""
                    select coalesce(sum(users), 0)::bigint as users,
                           coalesce(sum(new_users), 0)::bigint as new_users,
                           coalesce(sum(sessions), 0)::bigint as sessions,
                           coalesce(sum(engaged_sessions), 0)::bigint as engaged_sessions,
                           coalesce(sum(page_views), 0)::bigint as page_views,
                           coalesce(sum(engagement_seconds), 0)::double precision as engagement_seconds,
                           coalesce(sum(key_events), 0)::double precision as key_events,
                           coalesce(sum(revenue), 0)::double precision as revenue
                      from site_traffic_totals_daily
                     where site_id = :site_id and {WINDOW_FILTER}
                    """
                    ),
                    {"site_id": site_id, **window_params(last_day, days, offset_days)},
                )
            )
            .mappings()
            .first()
        )
        return TrafficTotals(
            users=int(row["users"] or 0),
            new_users=int(row["new_users"] or 0),
            sessions=int(row["sessions"] or 0),
            engaged_sessions=int(row["engaged_sessions"] or 0),
            page_views=int(row["page_views"] or 0),
            engagement_seconds=float(row["engagement_seconds"] or 0),
            key_events=float(row["key_events"] or 0),
            revenue=float(row["revenue"] or 0),
        )

    async def series(
        self, db: AsyncSession, site_id: str, last_day: str, days: int
    ) -> list[TrafficSeriesPoint]:
        rows = (
            (
                await db.execute(
                    text(
                        """
                    select day::text as day,
                           users, sessions, engaged_sessions, page_views, key_events, revenue
                      from site_traffic_totals_daily
                     where site_id = :site_id and day > :last_day - :span and day <= :last_day
                     order by day
                    """
                    ),
                    {"site_id": site_id, "last_day": day_value(last_day), "span": days},
                )
            )
            .mappings()
            .all()
        )
        return [
            TrafficSeriesPoint(
                day=str(r["day"]),
                users=int(r["users"] or 0),
                sessions=int(r["sessions"] or 0),
                engaged_sessions=int(r["engaged_sessions"] or 0),
                page_views=int(r["page_views"] or 0),
                key_events=float(r["key_events"] or 0),
                revenue=float(r["revenue"] or 0),
                organic_sessions=0,
            )
            for r in rows
        ]


site_traffic_totals_dailies = SiteTrafficTotalsDailyRepository()
