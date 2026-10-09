from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.scratchpad.constants import CLEANUP_EVERY_MINUTES
from src.scratchpad.cron.cleanup import cleanup

CLEANUP_ID = "scratchpad_cleanup"


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        cleanup,
        "interval",
        minutes=CLEANUP_EVERY_MINUTES,
        next_run_time=datetime.now(UTC),
        id=CLEANUP_ID,
        replace_existing=True,
        max_instances=1,
    )
