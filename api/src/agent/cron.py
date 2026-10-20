from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.concurrency import run_in_threadpool

from src.agent.workspace_expiry import sweep
from src.core.logging import get_logger
from src.settings import settings

log = get_logger()

SWEEP_ID = "workspace_expiry"


async def expire_workspaces() -> None:
    try:
        result = await run_in_threadpool(sweep)
    except Exception as exc:
        log.error("agent.cron.workspace_expiry_failed", error=str(exc))
        return
    if result.orphans or result.dropped or result.models:
        log.info(
            "agent.cron.workspaces_expired",
            orphans=result.orphans,
            dropped=result.dropped,
            models=result.models,
        )


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        expire_workspaces,
        "interval",
        minutes=settings.agent_workspace_sweep_minutes,
        next_run_time=datetime.now(UTC),
        id=SWEEP_ID,
        replace_existing=True,
        max_instances=1,
    )
