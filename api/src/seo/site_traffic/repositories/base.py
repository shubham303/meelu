import math
from datetime import UTC, date, datetime
from typing import Any, ClassVar

from sqlalchemy import Integer, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_traffic.reports import REPORT_SPECS, ReportSpec, snake
from src.seo.site_traffic.schemas import (
    TrafficReportRow,
    TrafficReportRowsResult,
    TrafficRollupResult,
    TrafficRollupRow,
)

WINDOW_FILTER = "day > :last_day - :span and day <= :last_day - :offset"


def day_value(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def window_params(last_day: str, days: int, offset_days: int = 0) -> dict[str, Any]:
    return {"last_day": day_value(last_day), "span": days + offset_days, "offset": offset_days}


def page_bounds(limit: int | None, offset: int | None) -> tuple[int, int]:
    return (
        min(max(limit if limit is not None else 50, 1), 200),
        max(offset if offset is not None else 0, 0),
    )


class TrafficDailyRepository:
    ID_PREFIX = "traf"
    INSERT_CHUNK = 1000
    REPORT: ClassVar[str]

    @property
    def spec(self) -> ReportSpec:
        return REPORT_SPECS[self.REPORT]

    async def upsert_chunk(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[dict[str, Any]]
    ) -> None:
        spec = self.spec
        integers = frozenset(
            c.key
            for c in inspect(spec.model).columns
            if isinstance(c.type, Integer) and c.key != "seq"
        )
        values = []
        for r in rows:
            row: dict[str, Any] = {
                "id": uid(self.ID_PREFIX),
                "user_id": user_id,
                "site_id": site_id,
                "day": day_value(r["day"]),
            }
            for f in (*spec.dims, *spec.metrics):
                column = snake(f)
                value = r[f]
                row[column] = (
                    math.floor(value + 0.5)
                    if column in integers and isinstance(value, float)
                    else value
                )
            values.append(row)
        if not values:
            return
        stmt = pg_insert(spec.model).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id", "day", *(snake(d) for d in spec.dims)],
            set_={
                **{snake(m): getattr(stmt.excluded, snake(m)) for m in spec.metrics},
                "updated_at": datetime.now(UTC),
            },
        )
        await db.execute(stmt)

    async def list_rows(
        self,
        db: AsyncSession,
        site_id: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> TrafficReportRowsResult:
        spec = self.spec
        limit = min(max(limit if limit is not None else 5000, 1), 10_000)
        offset = max(offset if offset is not None else 0, 0)
        fields = [*spec.dims, *spec.metrics]
        cols = ", ".join(f'{snake(f)} as "{f}"' for f in fields)
        rows = (
            (
                await db.execute(
                    text(
                        f"""
                    select day::text as day, {cols}, count(*) over ()::int as total
                      from {spec.name}
                     where site_id = :site_id
                     order by day, seq
                     limit :limit offset :offset
                    """
                    ),
                    {"site_id": site_id, "limit": limit, "offset": offset},
                )
            )
            .mappings()
            .all()
        )
        total = int(rows[0]["total"]) if rows else 0
        out = []
        for r in rows:
            row: dict[str, Any] = {"day": str(r["day"])}
            for d in spec.dims:
                row[d] = str(r[d]) if r[d] is not None else ""
            for m in spec.metrics:
                row[m] = float(r[m] or 0) if isinstance(r[m], float) else int(r[m] or 0)
            out.append(TrafficReportRow.model_validate(row))
        return TrafficReportRowsResult(rows=out, total=total)


class TrafficRollupRepository(TrafficDailyRepository):
    ROLLUP_METRICS: ClassVar[dict[str, str]]
    ROLLUP_DIMS: ClassVar[tuple[tuple[str, ...], ...]]

    async def rollup(
        self,
        db: AsyncSession,
        site_id: str,
        dims: tuple[str, ...],
        last_day: str,
        days: int,
        limit: int | None = None,
        offset: int | None = None,
        search: str | None = None,
    ) -> TrafficRollupResult:
        if dims not in self.ROLLUP_DIMS:
            raise ValueError(f"{self.spec.name} cannot be rolled up by {dims}")
        m = self.ROLLUP_METRICS
        table = self.spec.name
        limit, offset = page_bounds(limit, offset)
        dim_sql = ", ".join(dims)
        search_filter = f"and {dims[0]} ilike :search" if search else ""
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
                      select {dim_sql},
                             sum({m["sessions"]})::bigint as sessions,
                             sum({m["users"]})::bigint as users,
                             sum({m["engaged"]})::bigint as engaged_sessions,
                             sum({m["key"]})::double precision as key_events,
                             sum({m["revenue"]})::double precision as revenue
                        from {table}
                       where site_id = :site_id
                         and day > :last_day - :span and day <= :last_day
                         {search_filter}
                       group by {dim_sql}
                    ),
                    prev as (
                      select {dim_sql}, sum({m["sessions"]})::bigint as sessions
                        from {table}
                       where site_id = :site_id
                         and day > :last_day - :span2 and day <= :last_day - :span
                         {search_filter}
                       group by {dim_sql}
                    )
                    select cur.*, coalesce(prev.sessions, 0)::bigint as prev_sessions,
                           count(*) over ()::int as total
                      from cur
                      left join prev using ({dim_sql})
                     order by cur.sessions desc
                     limit :limit offset :offset
                    """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )

        return TrafficRollupResult(
            total=int(rows[0]["total"]) if rows else 0,
            rows=[
                TrafficRollupRow(
                    key=[str(r[d]) if r[d] is not None else "" for d in dims],
                    sessions=int(r["sessions"] or 0),
                    prev_sessions=int(r["prev_sessions"] or 0),
                    users=int(r["users"] or 0),
                    engaged_sessions=int(r["engaged_sessions"] or 0),
                    key_events=float(r["key_events"] or 0),
                    revenue=float(r["revenue"] or 0),
                )
                for r in rows
            ],
        )
