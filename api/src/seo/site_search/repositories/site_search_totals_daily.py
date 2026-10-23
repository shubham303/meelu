from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_search.models.site_search_totals_daily import SiteSearchTotalsDaily
from src.seo.site_search.repositories.site_search_daily import _day, _totals_row
from src.seo.site_search.schemas import (
    SearchCoverageRecord,
    SearchDailyPoint,
    SearchTotals,
    SearchTotalsRowInput,
)


class SiteSearchTotalsDailyRepository:
    async def replace_day(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        day: str,
        rows: list[SearchTotalsRowInput],
        final: bool,
    ) -> int:
        await db.execute(
            delete(SiteSearchTotalsDaily).where(
                SiteSearchTotalsDaily.site_id == site_id, SiteSearchTotalsDaily.day == _day(day)
            )
        )
        by_device = {r.device: r for r in rows}
        if by_device:
            await db.execute(
                insert(SiteSearchTotalsDaily),
                [
                    {
                        "id": uid("sst"),
                        "user_id": user_id,
                        "site_id": site_id,
                        "day": _day(day),
                        "device": r.device,
                        "clicks": r.clicks,
                        "impressions": r.impressions,
                        "position": r.position,
                        "final": final,
                    }
                    for r in by_device.values()
                ],
            )
        return len(by_device)

    async def coverage(self, db: AsyncSession, site_id: str) -> SearchCoverageRecord:
        row = (
            (
                await db.execute(
                    text(
                        """
                    select min(day)::text as first_day,
                           max(day)::text as last_day,
                           min(day) filter (where not final)::text as fresh_from,
                           count(distinct day)::int as days_stored,
                           coalesce(sum(impressions) filter (where day > current_date - 31), 0)::bigint as recent
                      from site_search_totals_daily
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
            fresh_from=row["fresh_from"] if row else None,
            days_stored=int(row["days_stored"] or 0) if row else 0,
            impressions_28d=int(row["recent"] or 0) if row else 0,
        )

    async def last_final_day(self, db: AsyncSession, site_id: str) -> str | None:
        value = (
            await db.execute(
                text(
                    "select max(day)::text from site_search_totals_daily "
                    "where site_id = :site_id and final"
                ),
                {"site_id": site_id},
            )
        ).scalar()
        return value

    async def totals_for_window(
        self, db: AsyncSession, site_id: str, last_day: str, days: int, offset_days: int = 0
    ) -> SearchTotals:
        row = (
            (
                await db.execute(
                    text(
                        """
                    select coalesce(sum(clicks), 0)::bigint as clicks,
                           coalesce(sum(impressions), 0)::bigint as impressions,
                           sum(position * impressions) / nullif(sum(impressions), 0) as position
                      from site_search_totals_daily
                     where site_id = :site_id
                       and day > :last_day - :span
                       and day <= :last_day - :offset
                    """
                    ),
                    {
                        "site_id": site_id,
                        "last_day": _day(last_day),
                        "span": days + offset_days,
                        "offset": offset_days,
                    },
                )
            )
            .mappings()
            .first()
        )
        return _totals_row(row)

    async def daily_series(
        self, db: AsyncSession, site_id: str, last_day: str, days: int
    ) -> list[SearchDailyPoint]:
        rows = (
            (
                await db.execute(
                    text(
                        """
                    select day::text as day,
                           sum(clicks)::bigint as clicks,
                           sum(impressions)::bigint as impressions,
                           sum(position * impressions) / nullif(sum(impressions), 0) as position
                      from site_search_totals_daily
                     where site_id = :site_id
                       and day > :last_day - :span
                       and day <= :last_day
                     group by 1
                     order by 1
                    """
                    ),
                    {"site_id": site_id, "last_day": _day(last_day), "span": days},
                )
            )
            .mappings()
            .all()
        )
        return [
            SearchDailyPoint(
                day=str(r["day"]),
                page=None,
                clicks=int(r["clicks"]),
                impressions=int(r["impressions"]),
                position=float(r["position"]) if r["position"] is not None else None,
            )
            for r in rows
        ]

    async def weekly_clicks(
        self, db: AsyncSession, site_id: str, last_day: str, weeks: int
    ) -> list[int]:
        rows = (
            (
                await db.execute(
                    text(
                        """
                    select floor((:last_day - day) / 7)::int as weeks_back,
                           sum(clicks)::bigint as clicks
                      from site_search_totals_daily
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


site_search_totals = SiteSearchTotalsDailyRepository()
