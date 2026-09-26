from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.schemas import EntityModel
from src.seo.jobs.schemas import SeoJobCreateRequest, SeoJobUpdateRequest
from src.seo.jobs.service import seo_job_service
from src.seo.pipeline.schemas import (
    ReconcileResult,
)
from src.seo.service import seo_service


class StartedJob(EntityModel):
    job_id: str
    reconciled: ReconcileResult
    ready: dict[str, int]


class FinishedJob(EntityModel):
    job_id: str
    status: str


@tool(writes=True, desk="seo")
async def start_seo_job(prompt: str) -> StartedJob:
    """Open an SEO job for the prompt you are about to run and get its job_id; every
    suggestion you save carries it. Reconciles first and reports the site's standing ready
    rows per action."""
    ctx = require_site()
    async with unit_of_work() as db:
        job, reconciled = await seo_service.start_job(
            db, ctx.user_id, ctx.site_id, SeoJobCreateRequest(prompt=prompt)
        )
        summary = await seo_service.overview(db, ctx.user_id, ctx.site_id)
    ready = {a: getattr(summary.suggestions, a).get("ready", 0) for a in ("add", "edit", "delete")}
    return StartedJob(job_id=job.id, reconciled=reconciled, ready=ready)


@tool(writes=True, desk="seo")
async def finish_seo_job(job_id: str, status: str = "COMPLETED") -> FinishedJob:
    """Close an SEO job as COMPLETED or FAILED once the prompt has run."""
    ctx = require_site()
    async with unit_of_work() as db:
        job = await seo_job_service.finish(
            db, ctx.site_id, job_id, SeoJobUpdateRequest(status=status)
        )
    return FinishedJob(job_id=job.id, status=job.status)
