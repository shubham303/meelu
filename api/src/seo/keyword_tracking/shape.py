from datetime import date
from typing import Any

from src.providers.seo_data.shape import own_domain
from src.seo.keyword_tracking.constants import TRACKED_DEPTH
from src.seo.keyword_tracking.schemas import RankRow, VolumeRow, normalize_keyword


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def whole(value: Any) -> int | None:
    found = number(value)
    return None if found is None else round(found)


def observed_on(raw: Any, fallback: date) -> date:
    if not isinstance(raw, str) or len(raw) < 10:
        return fallback
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return fallback


def month_of(row: dict) -> date | None:
    year, month = row.get("year"), row.get("month")
    if year is None or month is None:
        return None
    return date(int(year), int(month), 1)


def belongs_to(domain: str, site_domain: str) -> bool:
    return domain == site_domain or domain.endswith(f".{site_domain}")


def rank_rows(
    keyword: str,
    snapshot: dict,
    market: dict,
    source: str,
    site_domain: str,
    today: date,
) -> list[RankRow]:
    day = observed_on(snapshot.get("datetime"), today)
    rows: list[RankRow] = []
    for item in snapshot.get("items") or []:
        if not isinstance(item, dict) or item.get("type") != "organic" or not item.get("url"):
            continue
        rank = whole(item.get("rank_group"))
        if rank is None or rank > TRACKED_DEPTH:
            continue
        domain = own_domain(item.get("domain") or item["url"])
        rows.append(
            RankRow(
                keyword=keyword,
                location_code=market["location_code"],
                language_code=market["language_code"],
                observed_on=day,
                source=source,
                url=str(item["url"]),
                domain=domain,
                is_site=belongs_to(domain, site_domain),
                rank_group=rank,
                rank_absolute=whole(item.get("rank_absolute")),
                title=item.get("title"),
            )
        )
    return rows


def history_volume_rows(item: dict, market: dict) -> list[VolumeRow]:
    keyword = normalize_keyword(item.get("keyword") or "")
    volumes: dict[date, int | None] = {}
    costs: dict[date, tuple[float | None, float | None]] = {}
    for snapshot in sorted(
        (s for s in item.get("history") or [] if isinstance(s, dict) and month_of(s)),
        key=month_of,
    ):
        info = snapshot.get("keyword_info") or {}
        for row in info.get("monthly_searches") or []:
            if isinstance(row, dict) and (month := month_of(row)):
                volumes[month] = whole(row.get("search_volume"))
        costs[month_of(snapshot)] = (number(info.get("cpc")), number(info.get("competition")))
    return [
        VolumeRow(
            keyword=keyword,
            location_code=market["location_code"],
            language_code=market["language_code"],
            month=month,
            search_volume=volumes.get(month),
            cpc=costs.get(month, (None, None))[0],
            competition=costs.get(month, (None, None))[1],
        )
        for month in sorted(volumes.keys() | costs.keys())
    ]


def clickstream_volume_rows(item: dict, market: dict) -> list[VolumeRow]:
    keyword = normalize_keyword(item.get("keyword") or "")
    clickstream = (item.get("clickstream_keyword_info") or {}).get("monthly_searches") or []
    return [
        VolumeRow(
            keyword=keyword,
            location_code=market["location_code"],
            language_code=market["language_code"],
            month=month,
            clickstream_volume=whole(row.get("search_volume")),
        )
        for row in clickstream
        if isinstance(row, dict) and (month := month_of(row))
    ]
