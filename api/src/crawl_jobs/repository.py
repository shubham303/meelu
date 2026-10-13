from datetime import UTC, datetime, timedelta

from sqlalchemy import case, delete, func, null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.core.schemas import to_row
from src.crawl_jobs.models.site_crawl_job import SiteCrawlJob
from src.crawl_jobs.schemas import ACTIVE_JOB_STATUSES, CrawlJobFilters, CrawlJobRecord


class SiteCrawlJobRepository:
    ID_PREFIX = "scj"

    def _active(self):
        return SiteCrawlJob.status.in_(ACTIVE_JOB_STATUSES)

    def _fresh(self, stmt):
        return stmt.execution_options(populate_existing=True)

    def _record(self, row: SiteCrawlJob | None) -> CrawlJobRecord | None:
        return None if row is None else CrawlJobRecord.model_validate(row)

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> CrawlJobRecord | None:
        row = (
            await db.execute(
                self._fresh(
                    select(SiteCrawlJob)
                    .where(SiteCrawlJob.site_id == site_id, SiteCrawlJob.id == job_id)
                    .limit(1)
                )
            )
        ).scalar_one_or_none()
        return self._record(row)

    async def active(self, db: AsyncSession, site_id: str) -> CrawlJobRecord | None:
        row = (
            await db.execute(
                self._fresh(
                    select(SiteCrawlJob)
                    .where(SiteCrawlJob.site_id == site_id, self._active())
                    .limit(1)
                )
            )
        ).scalar_one_or_none()
        return self._record(row)

    async def latest(self, db: AsyncSession, site_id: str) -> CrawlJobRecord | None:
        row = (
            await db.execute(
                self._fresh(
                    select(SiteCrawlJob)
                    .where(SiteCrawlJob.site_id == site_id)
                    .order_by(SiteCrawlJob.seq.desc())
                    .limit(1)
                )
            )
        ).scalar_one_or_none()
        return self._record(row)

    async def last_frontier(self, db: AsyncSession, site_id: str) -> list[str]:
        found = (
            await db.execute(
                select(SiteCrawlJob.frontier)
                .where(
                    SiteCrawlJob.site_id == site_id,
                    SiteCrawlJob.status.in_(("completed", "cancelled")),
                )
                .order_by(SiteCrawlJob.seq.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return list(found or [])

    def _order(self, sort: str | None):
        if sort == "started":
            return SiteCrawlJob.started_at.desc().nulls_last()
        if sort == "finished":
            return SiteCrawlJob.finished_at.desc().nulls_last()
        if sort == "fetched":
            return SiteCrawlJob.fetched.desc()
        return SiteCrawlJob.seq.desc()

    def _conditions(self, site_id: str, f: CrawlJobFilters) -> list:
        conds = [SiteCrawlJob.site_id == site_id]
        if f.statuses:
            conds.append(SiteCrawlJob.status.in_(f.statuses))
        if f.trigger:
            conds.append(SiteCrawlJob.trigger == f.trigger)
        if f.active is not None:
            conds.append(self._active() if f.active else ~self._active())
        if f.complete is not None:
            conds.append(SiteCrawlJob.complete == f.complete)
        if f.failed is not None:
            conds.append(
                SiteCrawlJob.error.is_not(None) if f.failed else SiteCrawlJob.error.is_(None)
            )
        if f.started_after is not None:
            conds.append(SiteCrawlJob.started_at > f.started_after)
        if f.started_before is not None:
            conds.append(SiteCrawlJob.started_at < f.started_before)
        if f.finished_after is not None:
            conds.append(SiteCrawlJob.finished_at > f.finished_after)
        if f.finished_before is not None:
            conds.append(SiteCrawlJob.finished_at < f.finished_before)
        if f.created_after is not None:
            conds.append(SiteCrawlJob.created_at > f.created_after)
        if f.created_before is not None:
            conds.append(SiteCrawlJob.created_at < f.created_before)
        return conds

    async def list_filtered(
        self, db: AsyncSession, site_id: str, f: CrawlJobFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[CrawlJobRecord]:
        conds = self._conditions(site_id, f)
        total = (
            await db.execute(select(func.count()).select_from(SiteCrawlJob).where(*conds))
        ).scalar_one()
        rows = (
            (
                await db.execute(
                    self._fresh(
                        select(SiteCrawlJob)
                        .where(*conds)
                        .order_by(self._order(f.sort))
                        .offset(paging.offset)
                        .limit(paging.page_size)
                    )
                )
            )
            .scalars()
            .all()
        )
        return PaginatedApiResponse[CrawlJobRecord](
            data=[CrawlJobRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def open(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        *,
        trigger: str,
        sitemap_urls: list[str],
    ) -> CrawlJobRecord | None:
        now = datetime.now(UTC)
        stmt = (
            pg_insert(SiteCrawlJob)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                status="queued",
                trigger=trigger,
                sitemap_urls=sitemap_urls,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing()
            .returning(SiteCrawlJob)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        await db.flush()
        return self._record(row)

    async def start(self, db: AsyncSession, job_id: str) -> CrawlJobRecord | None:
        now = datetime.now(UTC)
        row = (
            await db.execute(
                update(SiteCrawlJob)
                .where(SiteCrawlJob.id == job_id, SiteCrawlJob.status == "queued")
                .values(status="running", started_at=now, heartbeat_at=now, updated_at=now)
                .returning(SiteCrawlJob)
            )
        ).scalar_one_or_none()
        await db.flush()
        return self._record(row)

    async def beat(
        self, db: AsyncSession, job_id: str, counters: dict[str, int]
    ) -> CrawlJobRecord | None:
        now = datetime.now(UTC)
        row = (
            await db.execute(
                update(SiteCrawlJob)
                .where(SiteCrawlJob.id == job_id)
                .values(**to_row(SiteCrawlJob, counters), heartbeat_at=now, updated_at=now)
                .returning(SiteCrawlJob)
            )
        ).scalar_one_or_none()
        await db.flush()
        return self._record(row)

    async def request_stop(
        self, db: AsyncSession, site_id: str, job_id: str, reason: str
    ) -> CrawlJobRecord | None:
        now = datetime.now(UTC)
        row = (
            await db.execute(
                update(SiteCrawlJob)
                .where(SiteCrawlJob.site_id == site_id, SiteCrawlJob.id == job_id, self._active())
                .values(
                    status=case((SiteCrawlJob.status == "queued", "cancelled"), else_="cancelling"),
                    finished_at=case((SiteCrawlJob.status == "queued", now), else_=null()),
                    stop_reason=reason,
                    updated_at=now,
                )
                .returning(SiteCrawlJob)
            )
        ).scalar_one_or_none()
        await db.flush()
        return self._record(row)

    async def settle(
        self, db: AsyncSession, job_id: str, status: str, patch: dict
    ) -> CrawlJobRecord | None:
        now = datetime.now(UTC)
        row = (
            await db.execute(
                update(SiteCrawlJob)
                .where(SiteCrawlJob.id == job_id)
                .values(
                    **to_row(SiteCrawlJob, patch), status=status, finished_at=now, updated_at=now
                )
                .returning(SiteCrawlJob)
            )
        ).scalar_one_or_none()
        await db.flush()
        return self._record(row)

    async def delete(self, db: AsyncSession, site_id: str, job_id: str) -> None:
        await db.execute(
            delete(SiteCrawlJob).where(SiteCrawlJob.site_id == site_id, SiteCrawlJob.id == job_id)
        )
        await db.flush()

    async def reap_stalled(
        self, db: AsyncSession, stale_ms: float, reason: str, site_ids: list[str] | None = None
    ) -> list[CrawlJobRecord]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(milliseconds=stale_ms)
        conds = [
            self._active(),
            func.coalesce(
                SiteCrawlJob.heartbeat_at, SiteCrawlJob.started_at, SiteCrawlJob.created_at
            )
            < cutoff,
        ]
        if site_ids:
            conds.append(SiteCrawlJob.site_id.in_(site_ids))

        rows = (
            (
                await db.execute(
                    update(SiteCrawlJob)
                    .where(*conds)
                    .values(
                        status="failed",
                        error=reason,
                        stop_reason=reason,
                        finished_at=now,
                        updated_at=now,
                    )
                    .returning(SiteCrawlJob)
                )
            )
            .scalars()
            .all()
        )
        await db.flush()
        return [CrawlJobRecord.model_validate(r) for r in rows]


site_crawl_jobs = SiteCrawlJobRepository()
