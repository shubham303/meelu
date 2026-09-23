import re
from datetime import date
from typing import Any
from urllib.parse import urlparse

from src.providers.seo_data.adapter import DEFAULT_LOCALE

MAX_URL = 2048


def locale_of(location_code: int | None, language_code: str | None) -> dict[str, Any]:
    return {
        "location_code": int(location_code or 0) or DEFAULT_LOCALE["location_code"],
        "language_code": (language_code or DEFAULT_LOCALE["language_code"]).lower(),
    }


def normalize_keywords(values: list[str] | None) -> list[str]:
    seen: dict[str, None] = {}
    for raw in values or []:
        keyword = re.sub(r"\s+", " ", str(raw or "").strip().lower())
        if keyword:
            seen[keyword] = None
    return list(seen)


def chunk(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def own_domain(domain: str | None) -> str:
    cleaned = re.sub(r"^[a-z]+://", "", str(domain or "").strip().lower())
    cleaned = re.sub(r"[/?#].*$", "", cleaned)
    return cleaned.removeprefix("www.")


def cited_urls(items: list) -> set[str]:
    urls: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key == "url" and isinstance(value, str):
                    urls.add(value)
                else:
                    walk(value)

    walk([i for i in items if isinstance(i, dict) and i.get("type") == "ai_overview"])
    return urls


def pick(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def round_value(value: Any) -> int | None:
    number = pick(value)
    return None if number is None else int(number + 0.5) if number >= 0 else int(number - 0.5)


def competition_index(competition: Any) -> int | None:
    number = pick(competition)
    return None if number is None else round(number * 100)


def months(rows: list | None) -> list[dict]:
    out = []
    for row in rows or []:
        if (
            not row
            or row.get("search_volume") is None
            or row.get("year") is None
            or row.get("month") is None
        ):
            continue
        out.append(
            {
                "month": f"{row['year']}-{int(row['month']):02d}-01",
                "volume": int(row["search_volume"]),
            }
        )
    return out


def clean_url(raw: Any) -> str | None:
    value = str(raw or "").strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return value[:MAX_URL]


def clip(raw: Any, cap: int) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value[:cap] if value else None


def fact_from_overview(item: dict, at: str) -> dict:
    info = item.get("keyword_info") or {}
    return {
        "keyword": item["keyword"].strip().lower(),
        "volume": info.get("search_volume"),
        "competition": info.get("competition_level"),
        "competitionIndex": competition_index(info.get("competition")),
        "cpc": info.get("cpc"),
        "lowTopOfPageBid": info.get("low_top_of_page_bid"),
        "highTopOfPageBid": info.get("high_top_of_page_bid"),
        "difficulty": (item.get("keyword_properties") or {}).get("keyword_difficulty"),
        "intent": (item.get("search_intent_info") or {}).get("main_intent"),
        "volumeFetchedAt": at,
        "difficultyFetchedAt": at,
        "intentFetchedAt": at,
        "months": months(info.get("monthly_searches")),
    }


def idea_of(item: dict) -> dict:
    return {
        "keyword": item["keyword"].strip().lower(),
        "volume": (item.get("keyword_info") or {}).get("search_volume"),
        "difficulty": (item.get("keyword_properties") or {}).get("keyword_difficulty"),
        "cpc": (item.get("keyword_info") or {}).get("cpc"),
        "intent": (item.get("search_intent_info") or {}).get("main_intent"),
    }


def prompt_of(item: dict, platform: str) -> dict:
    return {
        "question": clip(item.get("question"), 500),
        "platform": platform,
        "aiSearchVolume": round_value(item.get("ai_search_volume")),
        "citedUrls": [
            u for u in (clean_url((s or {}).get("url")) for s in item.get("sources") or []) if u
        ],
        "coMentionedBrands": [
            b
            for b in (clip((e or {}).get("title"), 200) for e in item.get("brand_entities") or [])
            if b
        ],
        "firstSeen": clip(item.get("first_response_at"), 64),
        "lastSeen": clip(item.get("last_response_at"), 64),
    }


def ranked_row(item: dict, domain: str) -> dict | None:
    keyword = str((item.get("keyword_data") or {}).get("keyword") or "").strip().lower()
    serp = (item.get("ranked_serp_element") or {}).get("serp_item")
    if not keyword or not serp:
        return None
    data = item.get("keyword_data") or {}
    info = data.get("keyword_info") or {}
    return {
        "domain": domain,
        "keyword": keyword,
        "rankGroup": int(serp.get("rank_group") or 0),
        "rankAbsolute": int(serp.get("rank_absolute") or 0),
        "url": serp.get("url"),
        "etv": pick(serp.get("etv")),
        "volume": info.get("search_volume"),
        "difficulty": (data.get("keyword_properties") or {}).get("keyword_difficulty"),
        "cpc": info.get("cpc"),
        "intent": (data.get("search_intent_info") or {}).get("main_intent"),
    }


def serp_questions(items: list) -> list[str]:
    questions: list[str] = []
    for block in items:
        if not isinstance(block, dict) or block.get("type") != "people_also_ask":
            continue
        for entry in block.get("items") or []:
            title = str((entry or {}).get("title") or "").strip()
            if title:
                questions.append(title)
    return questions


def serp_related(items: list) -> list[str]:
    related: list[str] = []
    for block in items:
        if not isinstance(block, dict) or block.get("type") != "related_searches":
            continue
        for entry in block.get("items") or []:
            term = (
                str(entry or "").strip()
                if not isinstance(entry, dict)
                else str(entry.get("title") or "")
            )
            if term:
                related.append(term)
    return related


def trend_points(graph: dict, keyword: str, seat: int) -> list[dict]:
    order = [str(k or "").strip().lower() for k in graph.get("keywords") or []]
    column = order.index(keyword) if keyword in order else seat
    points = []
    for point in graph.get("data") or []:
        day = str((point or {}).get("date_from") or "")[:10]
        try:
            date.fromisoformat(day)
        except ValueError:
            continue
        values = point.get("values") or []
        raw = values[column] if column < len(values) else None
        points.append({"day": day, "interest": int(raw or 0)})
    return points


def brand_filters(terms: list[str]) -> list:
    filters: list = []
    for term in terms:
        if filters:
            filters.append("and")
        filters.append(["keyword_data.keyword", "not_ilike", f"%{term}%"])
    return filters
