from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.logging import get_logger
from src.providers.social_search.store import purge as purge_store

log = get_logger("social_search.cron")

PURGE_ID = "social_search_store_purge"
PURGE_HOURS = 24


async def purge() -> None:
    try:
        removed = await purge_store()
    except Exception as exc:
        log.error("social_search_store_purge_failed", error=str(exc))
        return
    log.info("social_search_store_purged", **removed)


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        purge,
        "interval",
        hours=PURGE_HOURS,
        next_run_time=datetime.now(UTC),
        id=PURGE_ID,
        replace_existing=True,
        max_instances=1,
    )
