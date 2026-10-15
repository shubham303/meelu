import asyncio
import contextlib
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.providers.registry import Caller
from src.providers.social_search.service import social_search
from src.social_listening.identity import content_hash, native_id, post_key
from src.social_listening.repositories.cursors import social_listening_cursors
from src.social_listening.repositories.posts import social_listening_posts
from src.social_listening.repositories.queries import social_listening_queries
from src.social_listening.repositories.runs import social_listening_runs
from src.social_listening.repositories.social_posts import social_posts
from src.social_listening.schemas import LOOKBACK_DAYS, PER_KEYWORD

log = get_logger("social_listening.collect")

HEARTBEAT_SECONDS = 20
SILENT_AFTER_SECONDS = 90
SILENT_ERROR = "The search stopped reporting, most likely because the server restarted. Run again."


def running_stats() -> dict[str, Any]:
    return {"status": "running", "heartbeatAt": datetime.now(UTC).isoformat()}


def is_silent(stats: dict[str, Any], now: datetime) -> bool:
    if stats.get("status") != "running":
        return False
    beat = stats.get("heartbeatAt")
    try:
        last = datetime.fromisoformat(beat) if beat else None
    except ValueError:
        last = None
    return last is None or now - last > timedelta(seconds=SILENT_AFTER_SECONDS)


def normalize_keyword(keyword: str) -> str:
    return " ".join(str(keyword).lower().split())


def site_keywords(lines) -> list[str]:
    seen: dict[str, None] = {}
    for line in lines:
        for keyword in line.keywords or []:
            clean = normalize_keyword(keyword)
            if clean:
                seen[clean] = None
    return list(seen)


def keyword_windows(
    keywords: list[str], cursors: dict[str, datetime], now: datetime
) -> dict[str, datetime]:
    floor = now - timedelta(days=LOOKBACK_DAYS)
    return {k: max(cursors[k], floor) if k in cursors else floor for k in keywords}


def vendor_since(windows: dict[str, datetime]) -> datetime:
    return statistics.median_low(sorted(windows.values()))


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


async def _heartbeat(run_id: str, platform: str) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        try:
            async with unit_of_work() as db:
                await social_listening_runs.merge_platform_stats(
                    db, run_id, platform, running_stats()
                )
        except Exception as exc:
            log.warning(
                "collect_heartbeat_failed", run_id=run_id, platform=platform, error=str(exc)
            )


async def collect_platform(user_id: str, site_id: str, run_id: str, platform: str) -> None:
    stats: dict[str, Any] = {"status": "error"}
    union: list[str] = []
    beat = asyncio.create_task(_heartbeat(run_id, platform))
    try:
        stats, union = await _collect(user_id, site_id, run_id, platform)
    except Exception as exc:
        log.error("collect_failed", run_id=run_id, platform=platform, error=str(exc))
        stats = {"status": "error", "error": str(exc)}
    finally:
        beat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await beat
    async with unit_of_work() as db:
        await social_listening_runs.merge_platform_stats(
            db, run_id, platform, stats, fetched=len(union)
        )


async def _collect(
    user_id: str, site_id: str, run_id: str, platform: str
) -> tuple[dict[str, Any], list[str]]:
    async with unit_of_work() as db:
        run = await social_listening_runs.get(db, site_id, run_id)
        if run is None or run.status != "running":
            return {"status": "error", "error": "The run is no longer going."}, []
        started_at = run.started_at
        keywords = site_keywords(await social_listening_queries.list_enabled(db, site_id))
        cursors = await social_listening_cursors.by_keyword(db, site_id, platform, keywords)
    if not keywords:
        return {
            "status": "done",
            "keywords": 0,
            "fromVendor": 0,
            "fromDatabase": 0,
            "candidates": 0,
            "failedKeywords": [],
        }, []

    windows = keyword_windows(keywords, cursors, datetime.now(UTC))
    since = vendor_since(windows)
    error = None
    failed: list[str] = []
    vendor_posts: list[dict] = []
    try:
        result = await social_search.search_platform(
            Caller(user_id=user_id, site_id=site_id),
            platform,
            keywords,
            since.isoformat(),
            PER_KEYWORD,
        )
        vendor_posts = result.get("posts") or []
        failed = [normalize_keyword(k) for k in result.get("failedKeywords") or []]
    except Exception as exc:
        error = str(exc)
        failed = list(keywords)

    rows = {r["post_key"]: r for r in (social_post_row(p) for p in vendor_posts) if r}
    async with unit_of_work() as db:
        await social_posts.insert_new(db, list(rows.values()))
        vendor_ids = await social_posts.ids_by_keys(db, list(rows))
        database_ids: list[str] = []
        for keyword, window in windows.items():
            database_ids.extend(
                await social_posts.search_ids(db, platform, keyword, window, PER_KEYWORD)
            )
        union = list(dict.fromkeys([*vendor_ids, *database_ids]))
        candidates = await social_listening_posts.insert_candidates(
            db, user_id, site_id, run_id, union
        )
        succeeded = [k for k in keywords if k not in set(failed)]
        await social_listening_cursors.advance(
            db, user_id, site_id, platform, succeeded, started_at
        )

    stats = {
        "status": "done",
        "keywords": len(keywords),
        "fromVendor": len(vendor_ids),
        "fromDatabase": len(set(database_ids) - set(vendor_ids)),
        "candidates": candidates,
        "failedKeywords": failed,
    }
    if error:
        stats["error"] = error
    return stats, union
