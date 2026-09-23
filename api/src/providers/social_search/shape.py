import math
import re
from datetime import UTC, datetime
from typing import Any


def number_or_none(value: Any) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(n) else n


def iso_date(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        seconds = value / 1000 if value > 1e12 else value
        try:
            return datetime.fromtimestamp(seconds, UTC).isoformat()
        except (OverflowError, OSError, ValueError):
            return datetime.now(UTC).isoformat()
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(UTC).isoformat()
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).isoformat()


def post(platform: str, raw: dict[str, Any]) -> dict | None:
    url = str(raw.get("url") or "").strip()
    if not url:
        return None
    text = str(raw.get("text") or "").strip()
    title = str(raw["title"]).strip() if raw.get("title") is not None else None
    if not text and not title:
        return None
    tags = raw.get("tags")
    return {
        "id": str(raw.get("id") or url),
        "url": url,
        "platform": platform,
        "author": {
            "handle": str(raw.get("handle") or "unknown"),
            "displayName": str(raw["displayName"]) if raw.get("displayName") is not None else None,
        },
        "title": title or None,
        "text": text,
        "createdAt": iso_date(raw.get("createdAt")),
        "engagement": {
            "score": number_or_none(raw.get("score")),
            "comments": number_or_none(raw.get("comments")),
            "views": number_or_none(raw.get("views")),
        },
        "context": {
            "subreddit": str(raw["subreddit"]) if raw.get("subreddit") is not None else None,
            "tags": [str(t) for t in tags if t] if isinstance(tags, list) else None,
        },
    }


def strip_html(html: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(html or ""))
    for entity, char in (
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def epoch_seconds(since: Any) -> int | None:
    raw = str(since or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return int((parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).timestamp())


def since_day(since: Any) -> str | None:
    day = str(since or "")[:10]
    return day if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) else None
