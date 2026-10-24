from datetime import UTC, datetime, timedelta
from typing import Any

from src.providers.social_search.store import social_post_row
from src.social_listening.schemas import WebPost

FUTURE_SLACK = timedelta(days=1)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def web_post_rows(
    platform: str, posts: list[WebPost], oldest: datetime, now: datetime
) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for post in posts:
        posted = aware(post.posted_at)
        if posted < oldest or posted > now + FUTURE_SLACK:
            continue
        row = social_post_row(
            {
                "url": post.url,
                "platform": platform,
                "title": post.title,
                "text": post.text,
                "author": {"handle": post.author_handle, "displayName": post.author_name},
                "createdAt": posted.isoformat(),
            }
        )
        if row and (row["title"] or row["text"]):
            rows.setdefault(row["post_key"], row)
    return list(rows.values())


def web_stats(
    found: int,
    candidates: int,
    searched: int,
    failed: int,
    error: str | None,
    skipped: list[dict[str, str]],
) -> dict:
    nothing_ran = searched == 0 and not skipped
    stats: dict[str, Any] = {
        "status": "error" if nothing_ran or (searched and failed >= searched) else "done",
        "lines": searched,
        "failedLines": failed,
        "fromVendor": found,
        "fromDatabase": 0,
        "candidates": candidates,
        "skippedQueries": skipped,
    }
    if error:
        stats["error"] = error
    return stats
