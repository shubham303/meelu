from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import case, func, null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.render_jobs.models.site_page_render import SitePageRender
from src.render_jobs.models.site_render_job import SiteRenderJob
from src.render_jobs.schemas import (
    PageRenderCreateRequest,
    PageRenderRecord,
    RenderCandidateRecord,
    RenderCountsRecord,
    RenderJobRecord,
)
from src.site_pages.models.site_page import SitePage
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction

ACTIVE_JOB_STATUSES = ("queued", "running", "cancelling")

SAMPLE_PER_PAGE_TYPE = 10


def _active():
    return SiteRenderJob.status.in_(ACTIVE_JOB_STATUSES)


def _fresh(stmt):
    return stmt.execution_options(populate_existing=True)


def _job(row: SiteRenderJob | None) -> RenderJobRecord | None:
    return None if row is None else RenderJobRecord.model_validate(row)


async def job_by_id(db: AsyncSession, job_id: str) -> RenderJobRecord | None:
    result = await db.execute(
        _fresh(select(SiteRenderJob).where(SiteRenderJob.id == job_id).limit(1))
    )
    return _job(result.scalars().first())


async def active_job(
    db: AsyncSession, site_id: str, device: str | None = None
) -> RenderJobRecord | None:
    conds = [SiteRenderJob.site_id == site_id, _active()]
    if device:
        conds.append(SiteRenderJob.device == device)
    result = await db.execute(_fresh(select(SiteRenderJob).where(*conds).limit(1)))
    return _job(result.scalars().first())


async def latest_job(db: AsyncSession, site_id: str, device: str) -> RenderJobRecord | None:
    result = await db.execute(
        _fresh(
            select(SiteRenderJob)
            .where(SiteRenderJob.site_id == site_id, SiteRenderJob.device == device)
            .order_by(SiteRenderJob.seq.desc())
            .limit(1)
        )
    )
    return _job(result.scalars().first())


async def open_job(
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
            id=uid("srj"),
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
    return await job_by_id(db, job_id) if job_id else None


async def start_job(db: AsyncSession, job_id: str, total: int) -> bool:
    now = datetime.now(UTC)
    result = await db.execute(
        update(SiteRenderJob)
        .where(SiteRenderJob.id == job_id, SiteRenderJob.status == "queued")
        .values(status="running", total=total, started_at=now, heartbeat_at=now, updated_at=now)
        .returning(SiteRenderJob.id)
    )
    await db.flush()
    return result.scalar_one_or_none() is not None


async def beat_job(db: AsyncSession, job_id: str, counters: dict[str, int]) -> None:
    now = datetime.now(UTC)
    await db.execute(
        update(SiteRenderJob)
        .where(SiteRenderJob.id == job_id)
        .values(**counters, heartbeat_at=now, updated_at=now)
    )
    await db.flush()


async def request_job_stop(
    db: AsyncSession, site_id: str, job_id: str, reason: str
) -> RenderJobRecord | None:
    now = datetime.now(UTC)
    result = await db.execute(
        update(SiteRenderJob)
        .where(SiteRenderJob.site_id == site_id, SiteRenderJob.id == job_id, _active())
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
    return await job_by_id(db, stopped) if stopped else None


async def stop_requested(db: AsyncSession, job_id: str) -> bool:
    result = await db.execute(
        select(SiteRenderJob.status).where(SiteRenderJob.id == job_id).limit(1)
    )
    status = result.scalar_one_or_none()
    return status is None or status in ("cancelling", "cancelled")


async def settle_job(
    db: AsyncSession, job_id: str, status: str, values: dict[str, int | str]
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
    return await job_by_id(db, settled) if settled else None


async def reap_stalled_jobs(
    db: AsyncSession, stale_ms: float, reason: str, site_ids: list[str] | None = None
) -> list[RenderJobRecord]:
    now = datetime.now(UTC)
    cutoff = now - timedelta(milliseconds=stale_ms)
    conds = [
        _active(),
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
        .values(status="failed", error=reason, stop_reason=reason, finished_at=now, updated_at=now)
        .returning(SiteRenderJob.id)
    )
    ids = [row[0] for row in result.all()]
    await db.flush()
    if not ids:
        return []
    rows = (
        (await db.execute(_fresh(select(SiteRenderJob).where(SiteRenderJob.id.in_(ids)))))
        .scalars()
        .all()
    )
    return [RenderJobRecord.model_validate(row) for row in rows]


def _eligible():
    return (
        SitePage.status == 200,
        SitePage.shallow.is_(False),
        SitePage.blocked_by_robots.is_(False),
    )


async def candidates(
    db: AsyncSession,
    site_id: str,
    scope: str,
    device: str,
    page_limit: int | None = None,
    page_url: str | None = None,
) -> list[RenderCandidateRecord]:
    rank = (
        func.row_number()
        .over(
            partition_by=SitePageLlmExtraction.page_type,
            order_by=(SitePage.depth.asc().nulls_last(), SitePage.inlinks.desc(), SitePage.url),
        )
        .label("rank")
    )
    ranked = (
        select(
            SitePage.id.label("page_id"),
            SitePage.url,
            SitePageLlmExtraction.page_type,
            SitePage.content_hash,
            SitePageRender.rendered_from_hash,
            SitePage.seq,
            rank,
        )
        .join(
            SitePageRender,
            (SitePageRender.page_id == SitePage.id) & (SitePageRender.device == device),
            isouter=True,
        )
        .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id)
        .where(SitePage.site_id == site_id, *_eligible())
        .subquery()
    )
    query = select(
        ranked.c.page_id,
        ranked.c.url,
        ranked.c.page_type,
        ranked.c.content_hash,
        ranked.c.rendered_from_hash,
    ).order_by(ranked.c.seq)
    if page_url:
        query = query.where(ranked.c.url == page_url)
    elif scope == "sample":
        query = query.where(ranked.c.rank <= SAMPLE_PER_PAGE_TYPE)
    if page_limit:
        query = query.limit(page_limit)
    result = await db.execute(query)
    return [RenderCandidateRecord.model_validate(row) for row in result.all()]


async def page_exists(db: AsyncSession, site_id: str, page_id: str) -> bool:
    result = await db.execute(
        select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id == page_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def upsert_render(
    db: AsyncSession, user_id: str, site_id: str, body: PageRenderCreateRequest
) -> PageRenderRecord:
    now = datetime.now(UTC)
    values: dict[str, Any] = {**body.values(), "rendered_at": now, "updated_at": now}
    stmt = (
        pg_insert(SitePageRender)
        .values(
            id=uid("spr"),
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
    return await _render_by_id(db, saved)


async def _render_by_id(db: AsyncSession, render_id: str) -> PageRenderRecord:
    result = await db.execute(
        _fresh(select(SitePageRender).where(SitePageRender.id == render_id).limit(1))
    )
    return PageRenderRecord.model_validate(result.scalars().one())


async def get_render(
    db: AsyncSession, site_id: str, page_id: str, device: str
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


async def delete_render(db: AsyncSession, site_id: str, page_id: str, device: str) -> bool:
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


async def render_counts(db: AsyncSession, site_id: str, device: str) -> RenderCountsRecord:
    ok = (
        SitePageRender.site_id == site_id,
        SitePageRender.device == device,
        SitePageRender.render_error.is_(None),
    )
    rendered, last = (
        await db.execute(
            select(func.count(), func.max(SitePageRender.rendered_at))
            .select_from(SitePageRender)
            .where(*ok)
        )
    ).one()
    eligible_query = select(SitePage.id).where(SitePage.site_id == site_id, *_eligible())
    eligible = (
        await db.execute(select(func.count()).select_from(eligible_query.subquery()))
    ).scalar_one()
    fresh = (
        select(SitePageRender.page_id)
        .where(*ok)
        .where(SitePageRender.rendered_from_hash == SitePage.content_hash)
        .where(SitePageRender.page_id == SitePage.id)
    )
    pending = (
        await db.execute(
            select(func.count())
            .select_from(SitePage)
            .where(SitePage.site_id == site_id, *_eligible(), ~fresh.exists())
        )
    ).scalar_one()
    return RenderCountsRecord(
        rendered=rendered, eligible=eligible, pending=pending, last_rendered_at=last
    )
