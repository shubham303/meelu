import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.render_jobs import repository as repo
from src.render_jobs.repository import ACTIVE_JOB_STATUSES
from src.render_jobs.schemas import (
    PageRenderCreateRequest,
    PageRenderRecord,
    RenderJobBeatResult,
    RenderJobClaimResult,
    RenderJobOpenRequest,
    RenderJobRecord,
    RenderJobStartResult,
    RenderJobStatusRecord,
    RenderJobUpdateRequest,
    RenderTargetRecord,
)
from src.sites.service import get_site

STALE_JOB_MS = float(os.environ.get("MEELU_RENDER_STALE_MS", str(10 * 60 * 1000)))


async def _find_job(db: AsyncSession, site_id: str, job_id: str) -> RenderJobRecord:
    job = await repo.job_by_id(db, job_id)
    if job and job.site_id == site_id:
        return job
    raise HTTPException(404, f"No render job {job_id} for this website.")


async def start_render(
    db: AsyncSession, user_id: str, site_id: str, body: RenderJobOpenRequest
) -> RenderJobStartResult:
    target = await get_site(db, user_id, site_id)

    await repo.reap_stalled_jobs(
        db, STALE_JOB_MS, "the process running it stopped reporting", [site_id]
    )

    job = await repo.open_job(
        db, user_id, target.id, body.trigger, body.scope, body.device, body.user_agent_profile
    )
    if job is None:
        return RenderJobStartResult(
            started=False,
            job=await repo.active_job(db, target.id),
            reason=f"A render of {target.domain} is already running.",
        )

    return RenderJobStartResult(started=True, job=job)


async def claim_render(
    db: AsyncSession, user_id: str, site_id: str, job_id: str
) -> RenderJobClaimResult:
    job = await _find_job(db, site_id, job_id)
    target = await get_site(db, user_id, site_id)
    pages = await repo.candidates(db, target.id, job.scope, job.device)
    if not await repo.start_job(db, job.id, len(pages)):
        raise HTTPException(
            409,
            f"This render is {job.status} and will not run. Start a new one if you "
            f"meant to render again.",
        )
    started = await repo.job_by_id(db, job.id)
    if started is None:
        raise HTTPException(404, f"No render job {job_id} for this website.")
    return RenderJobClaimResult(
        job=started,
        target=RenderTargetRecord(
            site_id=target.id, domain=target.domain, robots_txt=target.robots_txt
        ),
        pages=pages,
    )


async def beat_render(
    db: AsyncSession, site_id: str, job_id: str, body: RenderJobUpdateRequest
) -> RenderJobBeatResult:
    job = await _find_job(db, site_id, job_id)
    await repo.beat_job(db, job.id, body.counters())
    return RenderJobBeatResult(stop=await repo.stop_requested(db, job.id))


async def settle_render(
    db: AsyncSession, user_id: str, site_id: str, job_id: str, body: RenderJobUpdateRequest
) -> RenderJobRecord:
    job = await _find_job(db, site_id, job_id)
    await get_site(db, user_id, site_id)

    values: dict[str, int | str] = dict(body.counters())
    if body.error is not None:
        values["error"] = body.error

    status = body.status if body.status in ("failed", "cancelled") else "completed"
    settled = await repo.settle_job(db, job.id, status, values)
    if settled is None:
        raise HTTPException(404, f"No render job {job_id} for this website.")
    return settled


async def stop_render(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    reason: str = "stopped by the user",
) -> RenderJobRecord:
    job = await _find_job(db, site_id, job_id)
    if job.status not in ACTIVE_JOB_STATUSES:
        raise HTTPException(
            409, f"That render already finished ({job.status}). There is nothing to stop."
        )
    stopped = await repo.request_job_stop(db, job.site_id, job.id, reason)
    if stopped is None:
        raise HTTPException(409, "That render settled before the stop arrived.")
    return stopped


async def reap_renders(
    db: AsyncSession,
    site_ids: list[str] | None = None,
    stale_ms: float = STALE_JOB_MS,
    reason: str = "no progress reported — the process running it is gone",
) -> list[RenderJobRecord]:
    return await repo.reap_stalled_jobs(db, stale_ms, reason, site_ids)


async def render_status(
    db: AsyncSession, user_id: str, site_id: str, device: str
) -> RenderJobStatusRecord:
    target = await get_site(db, user_id, site_id)
    counts = await repo.render_counts(db, target.id, device)
    active = await repo.active_job(db, target.id, device)
    latest = active if active is not None else await repo.latest_job(db, target.id, device)

    if latest is None:
        return RenderJobStatusRecord(
            site_id=target.id,
            device=device,
            state="idle",
            active=False,
            rendered_pages=counts.rendered,
            eligible_pages=counts.eligible,
            pending_pages=counts.pending,
            last_rendered_at=counts.last_rendered_at,
        )

    return RenderJobStatusRecord(
        site_id=target.id,
        device=device,
        job_id=latest.id,
        state=latest.status,
        active=active is not None,
        trigger=latest.trigger,
        scope=latest.scope,
        user_agent_profile=latest.user_agent_profile,
        started_at=latest.started_at,
        finished_at=latest.finished_at,
        total=latest.total,
        rendered=latest.rendered,
        failed=latest.failed,
        error=latest.error,
        stop_reason=latest.stop_reason,
        rendered_pages=counts.rendered,
        eligible_pages=counts.eligible,
        pending_pages=counts.pending,
        last_rendered_at=counts.last_rendered_at,
    )


async def save_page_render(
    db: AsyncSession, user_id: str, site_id: str, body: PageRenderCreateRequest
) -> PageRenderRecord:
    await get_site(db, user_id, site_id)
    if not await repo.page_exists(db, site_id, body.page_id):
        raise HTTPException(404, f"No page {body.page_id} for this website.")
    return await repo.upsert_render(db, user_id, site_id, body)


async def read_page_render(
    db: AsyncSession, user_id: str, site_id: str, page_id: str, device: str
) -> PageRenderRecord:
    await get_site(db, user_id, site_id)
    found = await repo.get_render(db, site_id, page_id, device)
    if found is None:
        raise HTTPException(404, f"Page {page_id} has not been rendered on {device}.")
    return found


async def delete_page_render(
    db: AsyncSession, user_id: str, site_id: str, page_id: str, device: str
) -> None:
    await get_site(db, user_id, site_id)
    if not await repo.delete_render(db, site_id, page_id, device):
        raise HTTPException(404, f"Page {page_id} has not been rendered on {device}.")
