from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.logging import get_logger
from src.credits.billing import site_billing_service
from src.settings import settings

log = get_logger("credits.cron")

SWEEP_ID = "credits_billing_sweep"


async def sweep() -> None:
    try:
        result = await site_billing_service.sweep()
    except Exception as exc:
        log.error("site_billing_sweep_failed", error=str(exc))
        return
    if result.considered:
        log.info("site_billing_sweep", **result.model_dump())


def register(scheduler: AsyncIOScheduler) -> None:
    if settings.credits_billing_sweep_disabled:
        return
    scheduler.add_job(
        sweep,
        "interval",
        seconds=settings.credits_billing_sweep_seconds,
        next_run_time=datetime.now(UTC),
        id=SWEEP_ID,
        replace_existing=True,
        max_instances=1,
    )
