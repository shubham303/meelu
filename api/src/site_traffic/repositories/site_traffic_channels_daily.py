from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_traffic.repositories.base import (
    WINDOW_FILTER,
    TrafficRollupRepository,
    day_value,
    window_params,
)
from src.site_traffic.schemas import TrafficChannelTotals


class SiteTrafficChannelsDailyRepository(TrafficRollupRepository):
    REPORT = "channels"
    ROLLUP_DIMS = (("channel",), ("source", "medium"))
    ROLLUP_METRICS = {
        "sessions": "sessions",
        "users": "users",
        "engaged": "engaged_sessions",
        "key": "key_events",
        "revenue": "revenue",
    }

    async def channel_totals(
        self,
        db: AsyncSession,
        site_id: str,
        last_day: str,
        days: int,
        channel: str,
        offset_days: int = 0,
    ) -> TrafficChannelTotals:
        row = (
            (
                await db.execute(
                    text(
                        f"""
                    select coalesce(sum(sessions), 0)::bigint as sessions,
                           coalesce(sum(engaged_sessions), 0)::bigint as engaged_sessions,
                           coalesce(sum(key_events), 0)::double precision as key_events,
                           coalesce(sum(revenue), 0)::double precision as revenue
                      from site_traffic_channels_daily
                     where site_id = :site_id and channel = :channel and {WINDOW_FILTER}
                    """
                    ),
                    {
                        "site_id": site_id,
                        "channel": channel,
                        **window_params(last_day, days, offset_days),
                    },
                )
            )
            .mappings()
            .first()
        )
        return TrafficChannelTotals(
            sessions=int(row["sessions"] or 0),
            engaged_sessions=int(row["engaged_sessions"] or 0),
            key_events=float(row["key_events"] or 0),
            revenue=float(row["revenue"] or 0),
        )

    async def daily_sessions_for_channel(
        self, db: AsyncSession, site_id: str, channel: str, last_day: str, days: int
    ) -> dict[str, int]:
        rows = (
            (
                await db.execute(
                    text(
                        """
                    select day::text as day, sum(sessions)::bigint as sessions
                      from site_traffic_channels_daily
                     where site_id = :site_id and channel = :channel
                       and day > :last_day - :span and day <= :last_day
                     group by day
                    """
                    ),
                    {
                        "site_id": site_id,
                        "channel": channel,
                        "last_day": day_value(last_day),
                        "span": days,
                    },
                )
            )
            .mappings()
            .all()
        )
        return {str(r["day"]): int(r["sessions"] or 0) for r in rows}


site_traffic_channels_dailies = SiteTrafficChannelsDailyRepository()
