from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.site_structure.jobs.service import structure_job_service

log = get_logger("site_structure.cron")


async def fail_stale_jobs() -> None:
    try:
        async with unit_of_work() as db:
            failed = await structure_job_service.fail_stale_jobs(db)
    except Exception as exc:
        log.error("structure_stale_jobs_failed", error=str(exc))
        return
    if failed:
        log.info("structure_stale_jobs", failed=failed)
