from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.site_structure.cron.stale_jobs import fail_stale_jobs

STALE_JOBS_ID = "site_structure_fail_stale_jobs"


def register(scheduler: AsyncIOScheduler) -> None:
    scheduler.add_job(
        fail_stale_jobs,
        "cron",
        minute=0,
        id=STALE_JOBS_ID,
        replace_existing=True,
        max_instances=1,
    )
