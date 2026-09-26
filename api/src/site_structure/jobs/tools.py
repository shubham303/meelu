from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.schemas import EntityModel
from src.site_structure.jobs.schemas import (
    JobStatus,
    StructureJobCreateRequest,
    StructureJobUpdateRequest,
)
from src.site_structure.jobs.service import structure_job_service


class StartedJob(EntityModel):
    job_id: str


class FinishedJob(EntityModel):
    job_id: str
    status: JobStatus


@tool(writes=True, desk="site")
async def start_structure_job(prompt: str) -> StartedJob:
    """Open a structure job for the prompt you are about to run and get its job_id; every
    suggestion you save carries it."""
    ctx = require_site()
    async with unit_of_work() as db:
        job = await structure_job_service.create(
            db, ctx.user_id, ctx.site_id, StructureJobCreateRequest(prompt=prompt)
        )
    return StartedJob(job_id=job.id)


@tool(writes=True, desk="site")
async def finish_structure_job(job_id: str, status: str = "COMPLETED") -> FinishedJob:
    """Close a structure job as COMPLETED or FAILED once the prompt has run."""
    ctx = require_site()
    async with unit_of_work() as db:
        job = await structure_job_service.finish(
            db, ctx.site_id, job_id, StructureJobUpdateRequest(status=status)
        )
    return FinishedJob(job_id=job.id, status=job.status)
