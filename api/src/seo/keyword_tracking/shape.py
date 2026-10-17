from datetime import date
from typing import Any

from src.seo.keyword_tracking.schemas import VolumeRow, normalize_keyword


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def whole(value: Any) -> int | None:
    found = number(value)
    return None if found is None else round(found)


def month_of(row: dict) -> date | None:
    year, month = row.get("year"), row.get("month")
    if year is None or month is None:
        return None
    return date(int(year), int(month), 1)


def monthly(info: dict | None) -> dict[date, int | None]:
    return {
        month: whole(row.get("search_volume"))
        for row in (info or {}).get("monthly_searches") or []
        if isinstance(row, dict) and (month := month_of(row))
    }


def volume_rows(item: dict, market: dict) -> list[VolumeRow]:
    keyword = normalize_keyword(item.get("keyword") or "")
    info = item.get("keyword_info") or {}
    ads = monthly(info)
    clickstream = monthly(item.get("clickstream_keyword_info"))
    latest = max(ads, default=None)
    return [
        VolumeRow(
            keyword=keyword,
            location_code=market["location_code"],
            language_code=market["language_code"],
            month=month,
            search_volume=ads.get(month),
            clickstream_volume=clickstream.get(month),
            cpc=number(info.get("cpc")) if month == latest else None,
            competition=number(info.get("competition")) if month == latest else None,
        )
        for month in sorted(ads.keys() | clickstream.keys())
    ]
