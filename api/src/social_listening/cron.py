from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.social_listening.service import social_listening_service

log = get_logger()

PURGE_ID = "social_listening_purge"
PURGE_HOURS = 24


async def purge() -> None:
    try:
        async with unit_of_work() as db:
            removed = await social_listening_service.purge(db)
    except Exception as exc:
        log.error("social_listening.cron.purge_failed", error=str(exc))
        return
    log.info("social_listening.cron.purged", **removed)


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
