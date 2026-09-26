from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.render_jobs.models.site_page_render import SitePageRender
from src.render_jobs.models.site_render_job import SiteRenderJob
from src.render_jobs.schemas import (
    ACTIVE_JOB_STATUSES,
    PageRenderCreateRequest,
    PageRenderRecord,
    RenderJobRecord,
)


class SiteRenderJobRepository:
    ID_PREFIX = "srj"

    def _active(self):
        return SiteRenderJob.status.in_(ACTIVE_JOB_STATUSES)

    def _fresh(self, stmt):
        return stmt.execution_options(populate_existing=True)

    def _job(self, row: SiteRenderJob | None) -> RenderJobRecord | None:
        return None if row is None else RenderJobRecord.model_validate(row)

    async def _by_id(self, db: AsyncSession, job_id: str) -> RenderJobRecord | None:
        result = await db.execute(
            self._fresh(select(SiteRenderJob).where(SiteRenderJob.id == job_id).limit(1))
        )
        return self._job(result.scalars().first())

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> RenderJobRecord | None:
        result = await db.execute(
            self._fresh(
                select(SiteRenderJob)
                .where(SiteRenderJob.site_id == site_id, SiteRenderJob.id == job_id)
                .limit(1)
            )
        )
        return self._job(result.scalars().first())

    async def active(
        self, db: AsyncSession, site_id: str, device: str | None = None
    ) -> RenderJobRecord | None:
        conds = [SiteRenderJob.site_id == site_id, self._active()]
        if device:
            conds.append(SiteRenderJob.device == device)
        result = await db.execute(self._fresh(select(SiteRenderJob).where(*conds).limit(1)))
        return self._job(result.scalars().first())

    async def latest(self, db: AsyncSession, site_id: str, device: str) -> RenderJobRecord | None:
        result = await db.execute(
            self._fresh(
                select(SiteRenderJob)
                .where(SiteRenderJob.site_id == site_id, SiteRenderJob.device == device)
                .order_by(SiteRenderJob.seq.desc())
                .limit(1)
            )
        )
        return self._job(result.scalars().first())

    async def open(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        trigger: str,
        scope: str,
        device: str,
        profile: str,
        page_limit: int | None = None,
        page_url: str | None = None,
    ) -> RenderJobRecord | None:
        now = datetime.now(UTC)
        stmt = (
            pg_insert(SiteRenderJob)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                status="queued",
                trigger=trigger,
                scope=scope,
                device=device,
                user_agent_profile=profile,
                page_limit=page_limit,
                page_url=page_url,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing()
            .returning(SiteRenderJob.id)
        )
        job_id = (await db.execute(stmt)).scalar_one_or_none()
        await db.flush()
        return await self._by_id(db, job_id) if job_id else None

    async def start(self, db: AsyncSession, job_id: str, total: int) -> bool:
        now = datetime.now(UTC)
        result = await db.execute(
            update(SiteRenderJob)
            .where(SiteRenderJob.id == job_id, SiteRenderJob.status == "queued")
            .values(status="running", total=total, started_at=now, heartbeat_at=now, updated_at=now)
            .returning(SiteRenderJob.id)
        )
        await db.flush()
        return result.scalar_one_or_none() is not None

    async def beat(self, db: AsyncSession, job_id: str, counters: dict[str, int]) -> None:
        now = datetime.now(UTC)
        await db.execute(
            update(SiteRenderJob)
            .where(SiteRenderJob.id == job_id)
            .values(**counters, heartbeat_at=now, updated_at=now)
        )
        await db.flush()

    async def request_stop(
        self, db: AsyncSession, site_id: str, job_id: str, reason: str
    ) -> RenderJobRecord | None:
        now = datetime.now(UTC)
        result = await db.execute(
            update(SiteRenderJob)
            .where(SiteRenderJob.site_id == site_id, SiteRenderJob.id == job_id, self._active())
            .values(
                status=case((SiteRenderJob.status == "queued", "cancelled"), else_="cancelling"),
                finished_at=case((SiteRenderJob.status == "queued", now), else_=null()),
                stop_reason=reason,
                updated_at=now,
            )
            .returning(SiteRenderJob.id)
        )
        stopped = result.scalar_one_or_none()
        await db.flush()
        return await self._by_id(db, stopped) if stopped else None

    async def stop_requested(self, db: AsyncSession, job_id: str) -> bool:
        result = await db.execute(
            select(SiteRenderJob.status).where(SiteRenderJob.id == job_id).limit(1)
        )
        status = result.scalar_one_or_none()
        return status is None or status in ("cancelling", "cancelled")

    async def settle(
        self, db: AsyncSession, job_id: str, status: str, values: dict[str, int | str]
    ) -> RenderJobRecord | None:
        now = datetime.now(UTC)
        result = await db.execute(
            update(SiteRenderJob)
            .where(SiteRenderJob.id == job_id)
            .values(**values, status=status, finished_at=now, updated_at=now)
            .returning(SiteRenderJob.id)
        )
        settled = result.scalar_one_or_none()
        await db.flush()
        return await self._by_id(db, settled) if settled else None

    async def reap_stalled(
        self, db: AsyncSession, stale_ms: float, reason: str, site_ids: list[str] | None = None
    ) -> list[RenderJobRecord]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(milliseconds=stale_ms)
        conds = [
            self._active(),
            func.coalesce(
                SiteRenderJob.heartbeat_at, SiteRenderJob.started_at, SiteRenderJob.created_at
            )
            < cutoff,
        ]
        if site_ids:
            conds.append(SiteRenderJob.site_id.in_(site_ids))

        result = await db.execute(
            update(SiteRenderJob)
            .where(*conds)
            .values(
                status="failed", error=reason, stop_reason=reason, finished_at=now, updated_at=now
            )
            .returning(SiteRenderJob.id)
        )
        ids = [row[0] for row in result.all()]
        await db.flush()
        if not ids:
            return []
        rows = (
            (await db.execute(self._fresh(select(SiteRenderJob).where(SiteRenderJob.id.in_(ids)))))
            .scalars()
            .all()
        )
        return [RenderJobRecord.model_validate(row) for row in rows]


class SitePageRenderRepository:
    ID_PREFIX = "spr"

    def _fresh(self, stmt):
        return stmt.execution_options(populate_existing=True)

    async def upsert(
        self, db: AsyncSession, user_id: str, site_id: str, body: PageRenderCreateRequest
    ) -> PageRenderRecord:
        now = datetime.now(UTC)
        values: dict[str, Any] = {**body.values(), "rendered_at": now, "updated_at": now}
        stmt = (
            pg_insert(SitePageRender)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                page_id=body.page_id,
                device=body.device,
                created_at=now,
                **values,
            )
            .on_conflict_do_update(
                index_elements=[SitePageRender.page_id, SitePageRender.device], set_=values
            )
            .returning(SitePageRender.id)
        )
        saved = (await db.execute(stmt)).scalar_one()
        await db.flush()
        return await self._by_id(db, saved)

    async def _by_id(self, db: AsyncSession, render_id: str) -> PageRenderRecord:
        result = await db.execute(
            self._fresh(select(SitePageRender).where(SitePageRender.id == render_id).limit(1))
        )
        return PageRenderRecord.model_validate(result.scalars().one())

    async def get(
        self, db: AsyncSession, site_id: str, page_id: str, device: str
    ) -> PageRenderRecord | None:
        result = await db.execute(
            select(SitePageRender)
            .where(
                SitePageRender.site_id == site_id,
                SitePageRender.page_id == page_id,
                SitePageRender.device == device,
            )
            .limit(1)
        )
        row = result.scalars().first()
        return None if row is None else PageRenderRecord.model_validate(row)

    async def delete(self, db: AsyncSession, site_id: str, page_id: str, device: str) -> bool:
        result = await db.execute(
            select(SitePageRender)
            .where(
                SitePageRender.site_id == site_id,
                SitePageRender.page_id == page_id,
                SitePageRender.device == device,
            )
            .limit(1)
        )
        row = result.scalars().first()
        if row is None:
            return False
        await db.delete(row)
        await db.flush()
        return True

    async def rendered_hashes_by_page_ids(
        self,
        db: AsyncSession,
        site_id: str,
        device: str,
        page_ids: list[str],
        ok_only: bool = False,
    ) -> dict[str, str | None]:
        if not page_ids:
            return {}
        conds: list[Any] = [
            SitePageRender.site_id == site_id,
            SitePageRender.device == device,
            SitePageRender.page_id.in_(set(page_ids)),
        ]
        if ok_only:
            conds.append(SitePageRender.render_error.is_(None))
        rows = await db.execute(
            select(SitePageRender.page_id, SitePageRender.rendered_from_hash).where(*conds)
        )
        return {r.page_id: r.rendered_from_hash for r in rows}

    async def rendered_summary(
        self, db: AsyncSession, site_id: str, device: str
    ) -> tuple[int, datetime | None]:
        rendered, last = (
            await db.execute(
                select(func.count(), func.max(SitePageRender.rendered_at)).where(
                    SitePageRender.site_id == site_id,
                    SitePageRender.device == device,
                    SitePageRender.render_error.is_(None),
                )
            )
        ).one()
        return int(rendered), last


site_render_jobs = SiteRenderJobRepository()
site_page_renders = SitePageRenderRepository()
