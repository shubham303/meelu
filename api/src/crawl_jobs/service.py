import math
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.crawl_jobs.repository import site_crawl_jobs
from src.crawl_jobs.schemas import (
    ACTIVE_JOB_STATUSES,
    CrawlJobCreateRequest,
    CrawlJobDeleteResponse,
    CrawlJobFilters,
    CrawlJobHeartbeatResponse,
    CrawlJobRecord,
    CrawlJobStartResponse,
    CrawlJobUpdateRequest,
    CrawlPlanResponse,
    CrawlStatusResponse,
    CrawlTargetResponse,
)
from src.seo.service import seo_service
from src.site_pages.repositories.pages import site_pages
from src.site_pages.service import site_page_service
from src.sites.repository import sites
from src.sites.schemas import SiteRecord
from src.sites.service import site_service
from src.technical_seo.rules.ai_crawlers import read_crawler_access
from src.technical_seo.rules.host_variants import read_host_variants

DEFAULT_FRESH_DAYS = float(os.environ.get("MEELU_CRAWL_FRESH_DAYS", "7"))

STALE_JOB_MS = float(os.environ.get("MEELU_CRAWL_STALE_MS", str(10 * 60 * 1000)))

CRAWL_BATCH = int(os.environ.get("MEELU_CRAWL_BATCH", "25"))

CRAWL_CONCURRENCY = int(os.environ.get("MEELU_CRAWL_CONCURRENCY", "8"))

HEARTBEAT_COUNTER_KEYS = ("discovered", "skipped", "fetched", "queued")

SETTLE_COUNTER_KEYS = (
    "discovered",
    "skipped",
    "fetched",
    "queued",
    "new_pages",
    "changed",
    "unchanged",
    "failed",
    "pages_stored",
)


class CrawlFreshness(BaseModel):
    at: datetime | None
    days: int | float


def _whole(days: float) -> int | float:
    return int(days) if float(days).is_integer() else days


def _freshness(fresh_days: float | None, fresh_before: datetime | None) -> CrawlFreshness:
    if fresh_before is not None:
        elapsed = (datetime.now(UTC) - fresh_before).total_seconds() / 86_400
        return CrawlFreshness(at=fresh_before, days=max(0, math.floor(elapsed + 0.5)))
    days = fresh_days if fresh_days is not None else DEFAULT_FRESH_DAYS
    if days <= 0:
        return CrawlFreshness(at=None, days=0)
    return CrawlFreshness(at=datetime.now(UTC) - timedelta(days=days), days=_whole(days))


class CrawlJobService:
    async def _plan(
        self, db: AsyncSession, target: SiteRecord, job: CrawlJobRecord
    ) -> CrawlPlanResponse:
        return CrawlPlanResponse(
            job=job,
            target=CrawlTargetResponse(site_id=target.id, domain=target.domain, name=target.name),
            fresh_before=job.fresh_before,
            sitemap_urls=job.sitemap_urls if job.sitemap_urls else target.sitemap_urls,
            concurrency=CRAWL_CONCURRENCY,
            batch_size=CRAWL_BATCH,
            known=await site_pages.crawl_known_pages(db, target.id),
            link_frontier=await site_page_service.link_frontier(db, target.id),
        )

    async def _find_job(self, db: AsyncSession, site_id: str, job_id: str) -> CrawlJobRecord:
        job = await site_crawl_jobs.get(db, site_id, job_id)
        if job is None:
            raise HTTPException(404, f"No crawl {job_id} for this website.")
        return job

    async def list_crawls(
        self, db: AsyncSession, site_id: str, filters: CrawlJobFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[CrawlJobRecord]:
        return await site_crawl_jobs.list_filtered(db, site_id, filters, paging)

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> CrawlJobRecord:
        return await self._find_job(db, site_id, job_id)

    async def delete(
        self, db: AsyncSession, user_id: str, site_id: str, job_id: str
    ) -> CrawlJobDeleteResponse:
        job = await self._find_job(db, site_id, job_id)
        if job.status in ACTIVE_JOB_STATUSES:
            stopped = await self.stop(db, user_id, site_id, job_id=job_id)
            return CrawlJobDeleteResponse(id=job.id, stopped=True, deleted=False, job=stopped)
        await site_crawl_jobs.delete(db, job.site_id, job.id)
        return CrawlJobDeleteResponse(id=job.id, stopped=False, deleted=True)

    async def start(
        self, db: AsyncSession, user_id: str, site_id: str, body: CrawlJobCreateRequest
    ) -> CrawlJobStartResponse:
        target = await site_service.get(db, user_id, site_id)

        reaped: list[CrawlJobRecord] = []
        if body.reap:
            reaped = await self.reap(db, [site_id], body.stale_ms or STALE_JOB_MS)

        await site_crawl_jobs.reap_stalled(
            db, STALE_JOB_MS, "the process running it stopped reporting", [site_id]
        )

        if body.sitemap_urls:
            await sites.merge(db, user_id, target.id, {"sitemap_urls": body.sitemap_urls})

        fresh = _freshness(body.fresh_days, body.fresh_before)
        job = await site_crawl_jobs.open(
            db,
            user_id,
            target.id,
            trigger=body.trigger,
            fresh_before=fresh.at,
            cutoff_days=fresh.days,
            sitemap_urls=body.sitemap_urls or [],
        )

        if job is None:
            return CrawlJobStartResponse(
                started=False,
                job=await site_crawl_jobs.active(db, target.id),
                reaped=reaped,
                reason=f"A crawl of {target.domain} is already running.",
            )

        return CrawlJobStartResponse(
            started=True, job=job, plan=await self._plan(db, target, job), reaped=reaped
        )

    async def claim(
        self, db: AsyncSession, user_id: str, site_id: str, job_id: str
    ) -> CrawlPlanResponse:
        job = await self._find_job(db, site_id, job_id)
        started = await site_crawl_jobs.start(db, job.id)
        if started is None:
            raise HTTPException(
                409,
                f"This crawl is {job.status} and will not run. Start a new one if you "
                f"meant to crawl again.",
            )
        target = await site_service.get(db, user_id, site_id)
        return await self._plan(db, target, started)

    async def beat(
        self, db: AsyncSession, site_id: str, job_id: str, body: CrawlJobUpdateRequest
    ) -> CrawlJobHeartbeatResponse:
        job = await self._find_job(db, site_id, job_id)
        beaten = await site_crawl_jobs.beat(db, job.id, body.counters(HEARTBEAT_COUNTER_KEYS))
        return CrawlJobHeartbeatResponse(
            stop=beaten is None or beaten.status in ("cancelling", "cancelled")
        )

    def _site_patch(self, body: CrawlJobUpdateRequest) -> dict[str, Any]:
        patch: dict[str, Any] = {"last_crawled_at": datetime.now(UTC)}

        if body.given("robots_txt"):
            patch["robots_txt"] = body.robots_txt
        if body.given("llms_txt"):
            patch["llms_txt"] = body.llms_txt
        if body.given("robots_status"):
            patch["robots_status"] = body.robots_status
        if body.given("llms_status"):
            patch["llms_status"] = body.llms_status
        if body.robots_fetched_at is not None:
            patch["robots_fetched_at"] = body.robots_fetched_at
        if body.llms_fetched_at is not None:
            patch["llms_fetched_at"] = body.llms_fetched_at

        if body.crawler_access:
            patch["crawler_access"] = read_crawler_access(body.crawler_access)
        if body.host_variants:
            patch["host_variants"] = read_host_variants(body.host_variants)

        if body.sitemap_url_count is not None:
            patch["sitemap_url_count"] = body.sitemap_url_count
        if body.sitemaps_used:
            patch["sitemap_urls"] = body.sitemaps_used
        if body.sitemap_at_root is not None:
            patch["sitemap_at_root"] = body.sitemap_at_root

        return patch

    async def settle(
        self, db: AsyncSession, user_id: str, site_id: str, job_id: str, body: CrawlJobUpdateRequest
    ) -> CrawlJobRecord:
        job = await self._find_job(db, site_id, job_id)
        target = await site_service.get(db, user_id, site_id)

        counters: dict[str, Any] = {
            **body.counters(SETTLE_COUNTER_KEYS),
            "complete": body.complete is True,
        }
        if body.notes is not None:
            counters["notes"] = body.notes
        if body.error is not None:
            counters["error"] = body.error

        if body.sitemap_complete is True and body.sitemap_urls:
            stamped = await site_pages.stamp_sitemap_presence(db, target.id, body.sitemap_urls)
            known, listed = stamped.known, stamped.listed
            if known >= 20 and listed < known / 2:
                counters["notes"] = [
                    *counters.get("notes", []),
                    f"The sitemap now lists {listed} of the {known} pages known for this "
                    f"site — that is a large drop; check the sitemap before treating those "
                    f"pages as retired.",
                ]

        status = body.status if body.status in ("failed", "cancelled") else "completed"
        settled = await site_crawl_jobs.settle(db, job.id, status, counters)
        if settled is None:
            raise HTTPException(404, f"No crawl {job_id} for this website.")

        await sites.merge(db, user_id, target.id, self._site_patch(body))
        if status == "completed":
            await seo_service.request_precompute(db, user_id, target.id)
        return settled

    async def stop(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        *,
        job_id: str | None = None,
        reason: str = "stopped by the user",
    ) -> CrawlJobRecord:
        found = (
            await self._find_job(db, site_id, job_id)
            if job_id
            else await site_crawl_jobs.active(db, site_id)
        )
        if found is None:
            raise HTTPException(404, "No crawl to stop for this website.")

        if found.status not in ACTIVE_JOB_STATUSES:
            raise HTTPException(
                409, f"That crawl already finished ({found.status}). There is nothing to stop."
            )

        stopped = await site_crawl_jobs.request_stop(db, found.site_id, found.id, reason)
        if stopped is None:
            raise HTTPException(409, "That crawl settled before the stop arrived.")
        return stopped

    async def reap(
        self,
        db: AsyncSession,
        site_ids: list[str] | None = None,
        stale_ms: float = STALE_JOB_MS,
        reason: str = "no progress reported — the process running it is gone",
    ) -> list[CrawlJobRecord]:
        return await site_crawl_jobs.reap_stalled(db, stale_ms, reason, site_ids)

    async def status(self, db: AsyncSession, user_id: str, site_id: str) -> CrawlStatusResponse:
        target = await site_service.get(db, user_id, site_id)
        page_count = await site_pages.count(db, target.id)
        active = await site_crawl_jobs.active(db, target.id)
        latest = active if active is not None else await site_crawl_jobs.latest(db, target.id)

        if latest is None:
            return CrawlStatusResponse(
                site_id=target.id,
                domain=target.domain,
                state="idle",
                active=False,
                last_crawled_at=target.last_crawled_at,
                sitemap_urls=target.sitemap_urls,
                pages=page_count,
            )

        return CrawlStatusResponse(
            site_id=target.id,
            domain=target.domain,
            job_id=latest.id,
            state=latest.status,
            active=active is not None,
            trigger=latest.trigger,
            started_at=latest.started_at,
            finished_at=latest.finished_at,
            fetched=latest.fetched,
            queued=latest.queued,
            skipped=latest.skipped,
            discovered=latest.discovered,
            error=latest.error,
            stop_reason=latest.stop_reason,
            cutoff_days=latest.cutoff_days,
            fresh_before=latest.fresh_before,
            last_crawled_at=target.last_crawled_at,
            last_crawl_complete=latest.complete,
            sitemap_urls=target.sitemap_urls,
            pages=page_count,
        )


crawl_job_service = CrawlJobService()
