import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.providers.registry import Caller, SpendMeter
from src.providers.social_search.store import collect_posts
from src.social_listening.repositories.cursors import social_listening_cursors
from src.social_listening.repositories.posts import social_listening_posts
from src.social_listening.repositories.queries import social_listening_queries
from src.social_listening.repositories.runs import social_listening_runs
from src.social_listening.schemas import LOOKBACK_DAYS, PER_KEYWORD

log = get_logger()

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
                "social_listening.collect.heartbeat_failed",
                run_id=run_id,
                platform=platform,
                error=str(exc),
            )


async def collect_platform(user_id: str, site_id: str, run_id: str, platform: str) -> None:
    stats: dict[str, Any] = {"status": "error"}
    union: list[str] = []
    beat = asyncio.create_task(_heartbeat(run_id, platform))
    try:
        stats, union = await _collect(user_id, site_id, run_id, platform)
    except Exception as exc:
        log.error(
            "social_listening.collect.failed", run_id=run_id, platform=platform, error=str(exc)
        )
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
            "costMicros": 0,
            "failedKeywords": [],
        }, []

    windows = keyword_windows(keywords, cursors, datetime.now(UTC))
    spend = SpendMeter()
    collected = await collect_posts(
        Caller(user_id=user_id, site_id=site_id, spend=spend), platform, windows, PER_KEYWORD
    )
    failed = [normalize_keyword(k) for k in collected.failed_keywords]
    vendor_ids = collected.vendor_ids
    database_ids = collected.database_ids
    union = collected.post_ids
    async with unit_of_work() as db:
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
        "costMicros": spend.micros,
        "failedKeywords": failed,
    }
    if collected.error:
        stats["error"] = collected.error
    return stats, union
