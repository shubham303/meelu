from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.connected_apps.service import connected_app_service
from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.settings import settings

log = get_logger()

SWEEP_ID = "connected_apps_sweep"


async def sweep() -> None:
    if not settings.composio_api_key:
        return
    try:
        async with unit_of_work() as db:
            removed = await connected_app_service.sweep(db)
    except Exception as exc:
        log.error("connected_apps.cron.sweep_failed", error=str(exc))
        return
    if removed:
        log.info("connected_apps.cron.swept", removed=removed)


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        sweep,
        "interval",
        minutes=settings.connected_apps_sweep_minutes,
        next_run_time=datetime.now(UTC),
        id=SWEEP_ID,
        replace_existing=True,
        max_instances=1,
    )
