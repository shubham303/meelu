import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Integer, inspect, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.site_traffic.models.site_traffic_sync import SiteTrafficSync
from src.site_traffic.reports import REPORT_SPECS, snake
from src.site_traffic.schemas import (
    TrafficChannelTotals,
    TrafficContentPageRow,
    TrafficContentPagesResult,
    TrafficDayRange,
    TrafficLandingPageRow,
    TrafficLandingPagesResult,
    TrafficReportRow,
    TrafficReportRowsResult,
    TrafficRollupResult,
    TrafficRollupRow,
    TrafficSeriesPoint,
    TrafficSyncRecord,
    TrafficTotals,
)

INSERT_CHUNK = 1000


def _day(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def _integer_columns(model: type) -> frozenset[str]:
    return frozenset(
        c.key for c in inspect(model).columns if isinstance(c.type, Integer) and c.key != "seq"
    )


async def upsert_report_chunk(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    report: str,
    rows: list[dict[str, Any]],
) -> None:
    spec = REPORT_SPECS[report]
    integers = _integer_columns(spec.model)
    values = []
    for r in rows:
        row: dict[str, Any] = {
            "id": uid("traf"),
            "user_id": user_id,
            "site_id": site_id,
            "day": _day(r["day"]),
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


async def list_report_rows(
    db: AsyncSession,
    site_id: str,
    report: str,
    limit: int | None = None,
    offset: int | None = None,
) -> TrafficReportRowsResult:
    spec = REPORT_SPECS[report]
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


async def day_range(db: AsyncSession, site_id: str) -> TrafficDayRange:
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


WINDOW_FILTER = "day > :last_day - :span and day <= :last_day - :offset"


def _window_params(last_day: str, days: int, offset_days: int = 0) -> dict[str, Any]:
    return {"last_day": _day(last_day), "span": days + offset_days, "offset": offset_days}


async def totals(
    db: AsyncSession, site_id: str, last_day: str, days: int, offset_days: int = 0
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
                {"site_id": site_id, **_window_params(last_day, days, offset_days)},
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


async def channel_totals(
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
                    **_window_params(last_day, days, offset_days),
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


async def daily_series(
    db: AsyncSession, site_id: str, last_day: str, days: int, organic_channel: str
) -> list[TrafficSeriesPoint]:
    rows = (
        (
            await db.execute(
                text(
                    """
                select t.day::text as day,
                       t.users, t.sessions, t.engaged_sessions, t.page_views, t.key_events, t.revenue,
                       coalesce(o.sessions, 0)::bigint as organic_sessions
                  from site_traffic_totals_daily t
                  left join (
                    select day, sum(sessions)::bigint as sessions
                      from site_traffic_channels_daily
                     where site_id = :site_id and channel = :channel
                     group by day
                  ) o on o.day = t.day
                 where t.site_id = :site_id and t.day > :last_day - :span and t.day <= :last_day
                 order by t.day
                """
                ),
                {
                    "site_id": site_id,
                    "channel": organic_channel,
                    "last_day": _day(last_day),
                    "span": days,
                },
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
            organic_sessions=int(r["organic_sessions"] or 0),
        )
        for r in rows
    ]


ROLLUPS: dict[str, dict[str, Any]] = {
    "channel": {"table": "site_traffic_channels_daily", "dims": ["channel"]},
    "source": {"table": "site_traffic_channels_daily", "dims": ["source", "medium"]},
    "event": {"table": "site_traffic_events_daily", "dims": ["event_name"]},
    "country": {"table": "site_traffic_geo_daily", "dims": ["country"]},
    "device": {"table": "site_traffic_tech_daily", "dims": ["device_category"]},
    "os": {"table": "site_traffic_tech_daily", "dims": ["os"]},
    "browser": {"table": "site_traffic_tech_daily", "dims": ["browser"]},
}

ROLLUP_METRICS: dict[str, dict[str, str]] = {
    "site_traffic_channels_daily": {
        "sessions": "sessions",
        "users": "users",
        "engaged": "engaged_sessions",
        "key": "key_events",
        "revenue": "revenue",
    },
    "site_traffic_events_daily": {
        "sessions": "event_count",
        "users": "users",
        "engaged": "0",
        "key": "key_events",
        "revenue": "0",
    },
    "site_traffic_geo_daily": {
        "sessions": "sessions",
        "users": "users",
        "engaged": "0",
        "key": "key_events",
        "revenue": "revenue",
    },
    "site_traffic_tech_daily": {
        "sessions": "sessions",
        "users": "users",
        "engaged": "0",
        "key": "0",
        "revenue": "0",
    },
}


async def rollup(
    db: AsyncSession,
    site_id: str,
    kind: str,
    last_day: str,
    days: int,
    limit: int | None = None,
    offset: int | None = None,
    search: str | None = None,
) -> TrafficRollupResult:
    cfg = ROLLUPS[kind]
    m = ROLLUP_METRICS[cfg["table"]]
    limit = min(max(limit if limit is not None else 50, 1), 200)
    offset = max(offset if offset is not None else 0, 0)
    dims = ", ".join(cfg["dims"])
    search_filter = f"and {cfg['dims'][0]} ilike :search" if search else ""
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
                  select {dims},
                         sum({m["sessions"]})::bigint as sessions,
                         sum({m["users"]})::bigint as users,
                         sum({m["engaged"]})::bigint as engaged_sessions,
                         sum({m["key"]})::double precision as key_events,
                         sum({m["revenue"]})::double precision as revenue
                    from {cfg["table"]}
                   where site_id = :site_id
                     and day > :last_day - :span and day <= :last_day
                     {search_filter}
                   group by {dims}
                ),
                prev as (
                  select {dims}, sum({m["sessions"]})::bigint as sessions
                    from {cfg["table"]}
                   where site_id = :site_id
                     and day > :last_day - :span2 and day <= :last_day - :span
                     {search_filter}
                   group by {dims}
                )
                select cur.*, coalesce(prev.sessions, 0)::bigint as prev_sessions,
                       count(*) over ()::int as total
                  from cur
                  left join prev using ({dims})
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
                key=[str(r[d]) if r[d] is not None else "" for d in cfg["dims"]],
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


LANDING_ORDERS = {
    "delta": "abs(cur.sessions - coalesce(prev.sessions, 0)) desc",
    "keyEvents": "cur.key_events desc",
    "revenue": "cur.revenue desc",
    "sessions": "cur.sessions desc",
}


async def by_landing_page(
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
    limit = min(max(limit if limit is not None else 50, 1), 200)
    offset = max(offset if offset is not None else 0, 0)
    channel_filter = "and channel = :channel" if channel else ""
    search_filter = "and landing_page ilike :search" if search else ""
    order = LANDING_ORDERS.get(sort or "sessions", LANDING_ORDERS["sessions"])
    params: dict[str, Any] = {
        "site_id": site_id,
        "last_day": _day(last_day),
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
                       p.id as page_id,
                       p.url,
                       p.title,
                       count(*) over ()::int as total
                  from cur
                  left join prev on prev.landing_page = cur.landing_page
                  left join site_pages p
                    on p.site_id = :site_id
                   and regexp_replace(regexp_replace(p.url, '^https?://[^/]+', ''), '/+$', '')
                       = regexp_replace(split_part(cur.landing_page, '?', 1), '/+$', '')
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
                page_id=r["page_id"],
                url=r["url"],
                title=r["title"],
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


PAGE_PATH_ORDERS = {
    "delta": "abs(cur.views - coalesce(prev.views, 0)) desc",
    "users": "cur.users desc",
    "keyEvents": "cur.key_events desc",
    "views": "cur.views desc",
}


async def by_page_path(
    db: AsyncSession,
    site_id: str,
    last_day: str,
    days: int,
    search: str | None = None,
    sort: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TrafficContentPagesResult:
    limit = min(max(limit if limit is not None else 50, 1), 200)
    offset = max(offset if offset is not None else 0, 0)
    search_filter = "and page_path ilike :search" if search else ""
    order = PAGE_PATH_ORDERS.get(sort or "views", PAGE_PATH_ORDERS["views"])
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


async def insert_sync(
    db: AsyncSession, user_id: str, site_id: str, trigger: str
) -> TrafficSyncRecord | None:
    stmt = (
        pg_insert(SiteTrafficSync)
        .values(id=uid("tsync"), user_id=user_id, site_id=site_id, trigger=trigger, status="queued")
        .on_conflict_do_nothing()
        .returning(SiteTrafficSync)
    )
    row = (await db.execute(stmt)).scalars().first()
    return None if row is None else TrafficSyncRecord.model_validate(row)


async def get_sync(db: AsyncSession, site_id: str, id: str) -> TrafficSyncRecord | None:
    result = await db.execute(
        select(SiteTrafficSync)
        .where(SiteTrafficSync.site_id == site_id, SiteTrafficSync.id == id)
        .limit(1)
    )
    row = result.scalars().first()
    return None if row is None else TrafficSyncRecord.model_validate(row)


async def list_syncs(
    db: AsyncSession, site_id: str, limit: int | None = None, offset: int | None = None
) -> list[TrafficSyncRecord]:
    result = await db.execute(
        select(SiteTrafficSync)
        .where(SiteTrafficSync.site_id == site_id)
        .order_by(SiteTrafficSync.seq.desc())
        .limit(min(max(limit if limit is not None else 20, 1), 100))
        .offset(max(offset if offset is not None else 0, 0))
    )
    return [TrafficSyncRecord.model_validate(r) for r in result.scalars().all()]


async def active_sync(db: AsyncSession, site_id: str) -> TrafficSyncRecord | None:
    result = await db.execute(
        select(SiteTrafficSync)
        .where(
            SiteTrafficSync.site_id == site_id,
            SiteTrafficSync.status.in_(["queued", "running"]),
        )
        .limit(1)
    )
    row = result.scalars().first()
    return None if row is None else TrafficSyncRecord.model_validate(row)


async def patch_sync(
    db: AsyncSession, site_id: str, id: str, patch: dict[str, Any]
) -> TrafficSyncRecord | None:
    values = dict(patch)
    for key in ("first_day", "last_day"):
        if isinstance(values.get(key), str):
            values[key] = date.fromisoformat(values[key])
    values["updated_at"] = datetime.now(UTC)
    stmt = (
        update(SiteTrafficSync)
        .where(SiteTrafficSync.site_id == site_id, SiteTrafficSync.id == id)
        .values(**values)
        .returning(SiteTrafficSync)
    )
    row = (await db.execute(stmt)).scalars().first()
    return None if row is None else TrafficSyncRecord.model_validate(row)


async def stale_syncs(db: AsyncSession, stale_ms: int) -> list[TrafficSyncRecord]:
    cutoff = datetime.now(UTC) - timedelta(milliseconds=stale_ms)
    result = await db.execute(
        select(SiteTrafficSync).where(
            SiteTrafficSync.status.in_(["queued", "running"]),
            text("coalesce(heartbeat_at, created_at) < :cutoff").bindparams(cutoff=cutoff),
        )
    )
    return [TrafficSyncRecord.model_validate(r) for r in result.scalars().all()]
