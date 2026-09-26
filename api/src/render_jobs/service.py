import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.render_jobs.repository import site_page_renders, site_render_jobs
from src.render_jobs.schemas import (
    ACTIVE_JOB_STATUSES,
    PageRenderCreateRequest,
    PageRenderRecord,
    RenderCandidateRecord,
    RenderCountsRecord,
    RenderJobBeatResult,
    RenderJobClaimResult,
    RenderJobOpenRequest,
    RenderJobRecord,
    RenderJobStartResult,
    RenderJobStatusRecord,
    RenderJobUpdateRequest,
    RenderTargetRecord,
)
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import RenderEligiblePage
from src.sites.service import site_service

STALE_JOB_MS = float(os.environ.get("MEELU_RENDER_STALE_MS", str(10 * 60 * 1000)))

SAMPLE_PER_PAGE_TYPE = 10


class RenderJobService:
    async def _find_job(self, db: AsyncSession, site_id: str, job_id: str) -> RenderJobRecord:
        job = await site_render_jobs.get(db, site_id, job_id)
        if job is not None:
            return job
        raise HTTPException(404, f"No render job {job_id} for this website.")

    async def start(
        self, db: AsyncSession, user_id: str, site_id: str, body: RenderJobOpenRequest
    ) -> RenderJobStartResult:
        target = await site_service.get(db, user_id, site_id)

        await site_render_jobs.reap_stalled(
            db, STALE_JOB_MS, "the process running it stopped reporting", [site_id]
        )

        job = await site_render_jobs.open(
            db,
            user_id,
            target.id,
            body.trigger,
            body.scope,
            body.device,
            body.user_agent_profile,
            body.limit,
            body.url,
        )
        if job is None:
            return RenderJobStartResult(
                started=False,
                job=await site_render_jobs.active(db, target.id),
                reason=f"A render of {target.domain} is already running.",
            )

        return RenderJobStartResult(started=True, job=job)

    async def claim(
        self, db: AsyncSession, user_id: str, site_id: str, job_id: str
    ) -> RenderJobClaimResult:
        job = await self._find_job(db, site_id, job_id)
        target = await site_service.get(db, user_id, site_id)
        pages = await self._candidates(
            db, target.id, job.scope, job.device, job.page_limit, job.page_url
        )
        if not await site_render_jobs.start(db, job.id, len(pages)):
            raise HTTPException(
                409,
                f"This render is {job.status} and will not run. Start a new one if you "
                f"meant to render again.",
            )
        started = await site_render_jobs.get(db, site_id, job.id)
        if started is None:
            raise HTTPException(404, f"No render job {job_id} for this website.")
        return RenderJobClaimResult(
            job=started,
            target=RenderTargetRecord(
                site_id=target.id, domain=target.domain, robots_txt=target.robots_txt
            ),
            pages=pages,
        )

    async def beat(
        self, db: AsyncSession, site_id: str, job_id: str, body: RenderJobUpdateRequest
    ) -> RenderJobBeatResult:
        job = await self._find_job(db, site_id, job_id)
        await site_render_jobs.beat(db, job.id, body.counters())
        return RenderJobBeatResult(stop=await site_render_jobs.stop_requested(db, job.id))

    async def settle(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        body: RenderJobUpdateRequest,
    ) -> RenderJobRecord:
        job = await self._find_job(db, site_id, job_id)
        await site_service.get(db, user_id, site_id)

        values: dict[str, int | str] = dict(body.counters())
        if body.error is not None:
            values["error"] = body.error

        status = body.status if body.status in ("failed", "cancelled") else "completed"
        settled = await site_render_jobs.settle(db, job.id, status, values)
        if settled is None:
            raise HTTPException(404, f"No render job {job_id} for this website.")
        return settled

    async def stop(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        reason: str = "stopped by the user",
    ) -> RenderJobRecord:
        job = await self._find_job(db, site_id, job_id)
        if job.status not in ACTIVE_JOB_STATUSES:
            raise HTTPException(
                409, f"That render already finished ({job.status}). There is nothing to stop."
            )
        stopped = await site_render_jobs.request_stop(db, job.site_id, job.id, reason)
        if stopped is None:
            raise HTTPException(409, "That render settled before the stop arrived.")
        return stopped

    async def reap(
        self,
        db: AsyncSession,
        site_ids: list[str] | None = None,
        stale_ms: float = STALE_JOB_MS,
        reason: str = "no progress reported — the process running it is gone",
    ) -> list[RenderJobRecord]:
        return await site_render_jobs.reap_stalled(db, stale_ms, reason, site_ids)

    async def status(
        self, db: AsyncSession, user_id: str, site_id: str, device: str
    ) -> RenderJobStatusRecord:
        target = await site_service.get(db, user_id, site_id)
        counts = await self._counts(db, target.id, device)
        active = await site_render_jobs.active(db, target.id, device)
        latest = (
            active if active is not None else await site_render_jobs.latest(db, target.id, device)
        )

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
        self, db: AsyncSession, user_id: str, site_id: str, body: PageRenderCreateRequest
    ) -> PageRenderRecord:
        await site_service.get(db, user_id, site_id)
        if not await site_pages.exists(db, site_id, body.page_id):
            raise HTTPException(404, f"No page {body.page_id} for this website.")
        return await site_page_renders.upsert(db, user_id, site_id, body)

    async def get_page_render(
        self, db: AsyncSession, user_id: str, site_id: str, page_id: str, device: str
    ) -> PageRenderRecord:
        await site_service.get(db, user_id, site_id)
        found = await site_page_renders.get(db, site_id, page_id, device)
        if found is None:
            raise HTTPException(404, f"Page {page_id} has not been rendered on {device}.")
        return found

    async def delete_page_render(
        self, db: AsyncSession, user_id: str, site_id: str, page_id: str, device: str
    ) -> None:
        await site_service.get(db, user_id, site_id)
        if not await site_page_renders.delete(db, site_id, page_id, device):
            raise HTTPException(404, f"Page {page_id} has not been rendered on {device}.")

    async def _candidates(
        self,
        db: AsyncSession,
        site_id: str,
        scope: str,
        device: str,
        page_limit: int | None = None,
        page_url: str | None = None,
    ) -> list[RenderCandidateRecord]:
        eligible = await site_pages.list_render_eligible(db, site_id, page_url or None)
        ids = [p.id for p in eligible]
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id, ids)
        rendered = await site_page_renders.rendered_hashes_by_page_ids(db, site_id, device, ids)
        if not page_url and scope == "sample":
            eligible = self._sample(eligible, types)
        if page_limit:
            eligible = eligible[:page_limit]
        return [
            RenderCandidateRecord(
                page_id=p.id,
                url=p.url,
                page_type=types.get(p.id),
                content_hash=p.content_hash,
                rendered_from_hash=rendered.get(p.id),
            )
            for p in eligible
        ]

    def _sample(
        self, pages: list[RenderEligiblePage], types: dict[str, str | None]
    ) -> list[RenderEligiblePage]:
        by_type: dict[str | None, list[RenderEligiblePage]] = {}
        for p in pages:
            by_type.setdefault(types.get(p.id), []).append(p)
        kept: set[str] = set()
        for group in by_type.values():
            ranked = sorted(
                group,
                key=lambda p: (p.depth is None, p.depth or 0, -p.inlinks, p.url),
            )
            kept.update(p.id for p in ranked[:SAMPLE_PER_PAGE_TYPE])
        return [p for p in pages if p.id in kept]

    async def _counts(self, db: AsyncSession, site_id: str, device: str) -> RenderCountsRecord:
        rendered, last = await site_page_renders.rendered_summary(db, site_id, device)
        eligible = await site_pages.list_render_eligible(db, site_id)
        fresh = await site_page_renders.rendered_hashes_by_page_ids(
            db, site_id, device, [p.id for p in eligible], ok_only=True
        )
        pending = sum(
            1 for p in eligible if p.content_hash is None or fresh.get(p.id) != p.content_hash
        )
        return RenderCountsRecord(
            rendered=rendered, eligible=len(eligible), pending=pending, last_rendered_at=last
        )


render_job_service = RenderJobService()
