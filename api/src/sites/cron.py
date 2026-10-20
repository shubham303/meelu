from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.settings import settings
from src.sites.service import site_service

log = get_logger()

PURGE_ID = "paused_site_purge"


async def purge() -> None:
    try:
        async with unit_of_work() as db:
            removed = await site_service.purge_paused(db)
    except Exception as exc:
        log.error("sites.cron.paused_purge_failed", error=str(exc))
        return
    for site in removed:
        log.info(
            "sites.cron.paused_site_deleted",
            site_id=site.id,
            user_id=site.user_id,
            domain=site.domain,
        )


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        purge,
        "interval",
        minutes=settings.sites_purge_minutes,
        next_run_time=datetime.now(UTC),
        id=PURGE_ID,
        replace_existing=True,
        max_instances=1,
    )
