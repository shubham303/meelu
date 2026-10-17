from datetime import date

from src.seo.keyword_tracking.constants import (
    DEMAND_SHIFT,
    HISTORY_MONTHS,
    MOVED_POSITIONS,
    SEASONAL_SWING,
)
from src.seo.keyword_tracking.schemas import TrackedKeyword, TrackedStats


def month_start(day: date) -> date:
    return day.replace(day=1)


def months_back(today: date, count: int) -> list[date]:
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(date(year, month, 1))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return list(reversed(months))


def demand(volumes: list[int]) -> str | None:
    if len(volumes) < 6:
        return None
    if min(volumes) > 0 and max(volumes) >= SEASONAL_SWING * min(volumes):
        return "seasonal"
    recent, before = sum(volumes[-3:]), sum(volumes[-6:-3])
    if before and recent >= (1 + DEMAND_SHIFT) * before:
        return "rising"
    if before and recent <= (1 - DEMAND_SHIFT) * before:
        return "falling"
    return "steady"


def tracked_keywords(
    months: list[date],
    positions: list[tuple[str, date, float, str]],
    volumes: list[tuple[str, date, int | None]],
) -> list[TrackedKeyword]:
    ranked: dict[str, dict[date, tuple[float, str]]] = {}
    for keyword, month, position, page in positions:
        ranked.setdefault(keyword, {})[month] = (position, page)
    monthly: dict[str, dict[date, int]] = {}
    for keyword, month, volume in volumes:
        if volume is not None:
            monthly.setdefault(keyword, {})[month] = volume

    rows = []
    for keyword in sorted(monthly.keys()):
        by_month = ranked.get(keyword, {})
        history = [round(by_month[m][0], 1) if m in by_month else None for m in months]
        seen = [m for m in months if m in by_month]
        latest = by_month[seen[-1]] if seen else None
        previous = by_month[seen[-2]] if len(seen) > 1 else None
        series = [monthly[keyword].get(m) for m in months]
        known = [v for v in series if v is not None]
        rows.append(
            TrackedKeyword(
                keyword=keyword,
                position=round(latest[0], 1) if latest else None,
                previous_position=round(previous[0], 1) if previous else None,
                change=round(previous[0] - latest[0], 1) if latest and previous else None,
                url=latest[1] if latest else None,
                history=history,
                volume=known[-1] if known else None,
                demand=demand(known[-HISTORY_MONTHS:]),
            )
        )
    return sorted(
        rows,
        key=lambda r: (r.position is None, r.position or 0, -(r.volume or 0), r.keyword),
    )


def stats(rows: list[TrackedKeyword]) -> TrackedStats:
    return TrackedStats(
        tracked=len(rows),
        top_ten=sum(1 for r in rows if r.position is not None and r.position <= 10),
        moved=sum(1 for r in rows if r.change is not None and abs(r.change) >= MOVED_POSITIONS),
        not_ranking=sum(1 for r in rows if r.position is None),
    )
