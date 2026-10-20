import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.providers.social_search.identity import content_hash, native_id, post_key
from src.providers.social_search.repository import social_posts, social_search_cursors
from src.providers.social_search.schemas import CollectedPosts
from src.providers.social_search.service import social_search

FRESH_HOURS = 6
RETENTION_DAYS = 30
MAX_POST_AGE_DAYS = RETENTION_DAYS


def social_post_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    url = str(raw.get("url") or "").strip()
    platform = str(raw.get("platform") or "").strip()
    if not url or not platform:
        return None
    raw_id = raw.get("id")
    external = str(raw_id) if raw_id is not None and str(raw_id) != url else None
    author = raw.get("author") or {}
    created = raw.get("createdAt")
    return {
        "post_key": post_key(platform, external, url),
        "external_id": native_id(platform, external, url),
        "platform": platform,
        "url": url,
        "title": raw.get("title"),
        "text": raw.get("text"),
        "author_handle": author.get("handle"),
        "author_name": author.get("displayName"),
        "posted_at": datetime.fromisoformat(created) if created else None,
        "engagement": raw.get("engagement") or {},
        "context": raw.get("context") or {},
        "content_hash": content_hash(raw.get("title"), raw.get("text")),
    }


def recent_enough(row: dict[str, Any], oldest: datetime) -> bool:
    posted = row.get("posted_at")
    return posted is None or posted >= oldest


def stale_keywords(
    windows: dict[str, datetime], fetched: dict[str, datetime], now: datetime
) -> dict[str, datetime]:
    fresh_after = now - timedelta(hours=FRESH_HOURS)
    return {
        keyword: max(since, fetched[keyword]) if keyword in fetched else since
        for keyword, since in windows.items()
        if keyword not in fetched or fetched[keyword] < fresh_after
    }


async def vendor_keywords(
    db: AsyncSession, platform: str, windows: dict[str, datetime]
) -> list[str]:
    fetched = await social_search_cursors.by_keyword(db, platform, list(windows))
    return list(stale_keywords(windows, fetched, datetime.now(UTC)))


async def collect_posts(
    caller: Caller, platform: str, windows: dict[str, datetime], per_keyword: int
) -> CollectedPosts:
    out = CollectedPosts()
    if not windows:
        return out
    started = datetime.now(UTC)
    async with unit_of_work() as db:
        fetched = await social_search_cursors.by_keyword(db, platform, list(windows))
    stale = stale_keywords(windows, fetched, started)
    out.vendor_keywords = list(stale)

    vendor_posts: list[dict] = []
    if stale:
        since = statistics.median_low(sorted(stale.values()))
        try:
            result = await social_search.search_platform(
                caller, platform, list(stale), since.isoformat(), per_keyword
            )
            vendor_posts = result.get("posts") or []
            out.failed_keywords = [str(k) for k in result.get("failedKeywords") or []]
        except Exception as exc:
            out.error = str(exc)
            out.failed_keywords = list(stale)

    oldest = started - timedelta(days=MAX_POST_AGE_DAYS)
    rows = {
        r["post_key"]: r
        for r in (social_post_row(p) for p in vendor_posts)
        if r and recent_enough(r, oldest)
    }
    async with unit_of_work() as db:
        await social_posts.insert_new(db, list(rows.values()))
        out.vendor_ids = await social_posts.ids_by_keys(db, list(rows))
        for keyword, since in windows.items():
            out.database_by_keyword[keyword] = await social_posts.search_ids(
                db, platform, keyword, since, oldest, per_keyword
            )
        failed = set(out.failed_keywords)
        await social_search_cursors.advance(
            db, platform, [k for k in stale if k not in failed], started
        )
    return out


async def purge() -> dict[str, int]:
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    async with unit_of_work() as db:
        return {
            "posts": await social_posts.delete_older_than(db, cutoff),
            "cursors": await social_search_cursors.delete_older_than(db, cutoff),
        }
