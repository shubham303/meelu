from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.identity.service import identity_service
from src.settings import settings

log = get_logger("identity.cron")

PURGE_ID = "expired_session_purge"


async def purge() -> None:
    try:
        async with unit_of_work() as db:
            removed = await identity_service.purge_expired_sessions(db)
    except Exception as exc:
        log.error("expired_session_purge_failed", error=str(exc))
        return
    if removed:
        log.info("expired_session_purge", removed=removed)


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        purge,
        "interval",
        minutes=settings.session_purge_minutes,
        next_run_time=datetime.now(UTC),
        id=PURGE_ID,
        replace_existing=True,
        max_instances=1,
    )
