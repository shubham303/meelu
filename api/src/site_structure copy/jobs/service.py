from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_structure.jobs.repository import structure_jobs
from src.site_structure.jobs.schemas import StructureJobRecord

STALE_AFTER = timedelta(hours=1)

NOT_FOUND = "No such structure job on this website."


async def require(db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord:
    found = await structure_jobs.get(db, site_id, job_id)
    if found is None:
        raise HTTPException(404, NOT_FOUND)
    return found


async def fail_stale_jobs(db: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - STALE_AFTER
    return await structure_jobs.fail_running_before(db, cutoff)
