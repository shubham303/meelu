from datetime import date

from src.seo.keyword_tracking.constants import DEMAND_SHIFT, HISTORY_MONTHS, SEASONAL_SWING
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
    days: list[tuple[str, date]],
    ranks: list[tuple[str, date, int, str]],
    volumes: list[tuple[str, date, int | None]],
) -> list[TrackedKeyword]:
    snapshot_days: dict[str, set[date]] = {}
    for keyword, day in days:
        snapshot_days.setdefault(keyword, set()).add(day)
    best: dict[tuple[str, date], tuple[int, str]] = {}
    for keyword, day, rank, url in ranks:
        found = best.get((keyword, day))
        if found is None or rank < found[0]:
            best[(keyword, day)] = (rank, url)
    monthly: dict[str, dict[date, int]] = {}
    for keyword, month, volume in volumes:
        if volume is not None:
            monthly.setdefault(keyword, {})[month] = volume

    rows = []
    for keyword in sorted(snapshot_days.keys() | monthly.keys()):
        ordered = sorted(snapshot_days.get(keyword, ()))
        latest = best.get((keyword, ordered[-1])) if ordered else None
        previous = best.get((keyword, ordered[-2])) if len(ordered) > 1 else None
        history = []
        for month in months:
            in_month = [
                best[(keyword, d)][0]
                for d in ordered
                if month_start(d) == month and (keyword, d) in best
            ]
            history.append(min(in_month) if in_month else None)
        series = [monthly.get(keyword, {}).get(m) for m in months]
        known = [v for v in series if v is not None]
        rows.append(
            TrackedKeyword(
                keyword=keyword,
                position=latest[0] if latest else None,
                previous_position=previous[0] if previous else None,
                change=previous[0] - latest[0] if latest and previous else None,
                url=latest[1] if latest else None,
                history=history,
                volume=known[-1] if known else None,
                demand=demand(known[-HISTORY_MONTHS:]),
                last_tracked=ordered[-1] if ordered else None,
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
        moved=sum(1 for r in rows if r.change),
        not_ranking=sum(1 for r in rows if r.position is None),
    )
