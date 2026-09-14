import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.analysis_jobs import repository as repo
from src.analysis_jobs.repository import ACTIVE_JOB_STATUSES
from src.analysis_jobs.schemas import (
    AnalysisJobBeatResult,
    AnalysisJobClaimResult,
    AnalysisJobRecord,
    AnalysisJobStartResult,
    AnalysisJobStatusRecord,
    AnalysisJobUpdateRequest,
    AnalysisTargetRecord,
    PageAnalysisCreateRequest,
    PageAnalysisRecord,
)
from src.sites.service import get_site

STALE_JOB_MS = float(os.environ.get("MEELU_ANALYZE_STALE_MS", str(10 * 60 * 1000)))


async def _find_job(db: AsyncSession, site_id: str, job_id: str) -> AnalysisJobRecord:
    job = await repo.job_by_id(db, job_id)
    if job and job.site_id == site_id:
        return job
    raise HTTPException(404, f"No page analysis {job_id} for this website.")


async def start_analysis(
    db: AsyncSession, user_id: str, site_id: str, trigger: str = "user"
) -> AnalysisJobStartResult:
    target = await get_site(db, user_id, site_id)

    await repo.reap_stalled_jobs(
        db, STALE_JOB_MS, "the process running it stopped reporting", [site_id]
    )

    job = await repo.open_job(db, user_id, target.id, trigger)
    if job is None:
        return AnalysisJobStartResult(
            started=False,
            job=await repo.active_job(db, target.id),
            reason=f"A page analysis of {target.domain} is already running.",
        )

    return AnalysisJobStartResult(started=True, job=job)


async def claim_analysis(
    db: AsyncSession, user_id: str, site_id: str, job_id: str
) -> AnalysisJobClaimResult:
    job = await _find_job(db, site_id, job_id)
    target = await get_site(db, user_id, site_id)
    pages = await repo.candidates(db, target.id)
    if not await repo.start_job(db, job.id, len(pages)):
        raise HTTPException(
            409,
            f"This analysis is {job.status} and will not run. Start a new one if you "
            f"meant to analyse again.",
        )
    started = await repo.job_by_id(db, job.id)
    if started is None:
        raise HTTPException(404, f"No page analysis {job_id} for this website.")
    return AnalysisJobClaimResult(
        job=started,
        target=AnalysisTargetRecord(site_id=target.id, domain=target.domain),
        pages=pages,
    )


async def beat_analysis(
    db: AsyncSession, site_id: str, job_id: str, body: AnalysisJobUpdateRequest
) -> AnalysisJobBeatResult:
    job = await _find_job(db, site_id, job_id)
    await repo.beat_job(db, job.id, body.counters())
    return AnalysisJobBeatResult(stop=await repo.stop_requested(db, job.id))


async def settle_analysis(
    db: AsyncSession, user_id: str, site_id: str, job_id: str, body: AnalysisJobUpdateRequest
) -> AnalysisJobRecord:
    job = await _find_job(db, site_id, job_id)
    await get_site(db, user_id, site_id)

    values: dict[str, int | str] = dict(body.counters())
    if body.error is not None:
        values["error"] = body.error

    status = body.status if body.status in ("failed", "cancelled") else "completed"
    settled = await repo.settle_job(db, job.id, status, values)
    if settled is None:
        raise HTTPException(404, f"No page analysis {job_id} for this website.")

    return settled


async def stop_analysis(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    reason: str = "stopped by the user",
) -> AnalysisJobRecord:
    job = await _find_job(db, site_id, job_id)
    if job.status not in ACTIVE_JOB_STATUSES:
        raise HTTPException(
            409, f"That analysis already finished ({job.status}). There is nothing to stop."
        )
    stopped = await repo.request_job_stop(db, job.site_id, job.id, reason)
    if stopped is None:
        raise HTTPException(409, "That analysis settled before the stop arrived.")
    return stopped


async def reap_analyses(
    db: AsyncSession,
    site_ids: list[str] | None = None,
    stale_ms: float = STALE_JOB_MS,
    reason: str = "no progress reported — the process running it is gone",
) -> list[AnalysisJobRecord]:
    return await repo.reap_stalled_jobs(db, stale_ms, reason, site_ids)


async def analysis_status(db: AsyncSession, user_id: str, site_id: str) -> AnalysisJobStatusRecord:
    target = await get_site(db, user_id, site_id)
    counts = await repo.analysis_counts(db, target.id)
    active = await repo.active_job(db, target.id)
    latest = active if active is not None else await repo.latest_job(db, target.id)

    if latest is None:
        return AnalysisJobStatusRecord(
            site_id=target.id,
            state="idle",
            active=False,
            analyzed_pages=counts.analyzed,
            eligible_pages=counts.eligible,
        )

    return AnalysisJobStatusRecord(
        site_id=target.id,
        job_id=latest.id,
        state=latest.status,
        active=active is not None,
        trigger=latest.trigger,
        started_at=latest.started_at,
        finished_at=latest.finished_at,
        total=latest.total,
        processed=latest.processed,
        skipped_unchanged=latest.skipped_unchanged,
        skipped_similar=latest.skipped_similar,
        failed=latest.failed,
        error=latest.error,
        stop_reason=latest.stop_reason,
        analyzed_pages=counts.analyzed,
        eligible_pages=counts.eligible,
    )


async def save_page_analysis(
    db: AsyncSession, user_id: str, site_id: str, body: PageAnalysisCreateRequest
) -> PageAnalysisRecord:
    await get_site(db, user_id, site_id)
    if not await repo.page_exists(db, site_id, body.page_id):
        raise HTTPException(404, f"No page {body.page_id} for this website.")

    if body.refresh_only:
        refreshed = await repo.refresh_hash(db, site_id, body.page_id, body.analyzed_from_hash)
        if refreshed is None:
            raise HTTPException(404, f"Page {body.page_id} has no analysis to refresh.")
        return refreshed

    return await repo.upsert_analysis(db, user_id, site_id, body)


async def read_page_analysis(
    db: AsyncSession, user_id: str, site_id: str, page_id: str
) -> PageAnalysisRecord:
    await get_site(db, user_id, site_id)
    found = await repo.get_analysis(db, site_id, page_id)
    if found is None:
        raise HTTPException(404, f"Page {page_id} has not been analysed.")
    return found
