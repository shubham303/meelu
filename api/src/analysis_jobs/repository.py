from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, null, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.analysis_jobs.models.site_analysis_job import SiteAnalysisJob
from src.analysis_jobs.models.site_page_analysis import SitePageAnalysis
from src.analysis_jobs.schemas import (
    AnalysisCandidateRecord,
    AnalysisCountsRecord,
    AnalysisJobRecord,
    PageAnalysisCreateRequest,
    PageAnalysisRecord,
)
from src.core.ids import uid
from src.site_pages.models.site_page import SitePage

ACTIVE_JOB_STATUSES = ("queued", "running", "cancelling")


def _active():
    return SiteAnalysisJob.status.in_(ACTIVE_JOB_STATUSES)


def _fresh(stmt):
    return stmt.execution_options(populate_existing=True)


def _job(row: SiteAnalysisJob | None) -> AnalysisJobRecord | None:
    return None if row is None else AnalysisJobRecord.model_validate(row)


async def job_by_id(db: AsyncSession, job_id: str) -> AnalysisJobRecord | None:
    result = await db.execute(
        _fresh(select(SiteAnalysisJob).where(SiteAnalysisJob.id == job_id).limit(1))
    )
    return _job(result.scalars().first())


async def active_job(db: AsyncSession, site_id: str) -> AnalysisJobRecord | None:
    result = await db.execute(
        _fresh(
            select(SiteAnalysisJob).where(SiteAnalysisJob.site_id == site_id, _active()).limit(1)
        )
    )
    return _job(result.scalars().first())


async def latest_job(db: AsyncSession, site_id: str) -> AnalysisJobRecord | None:
    result = await db.execute(
        _fresh(
            select(SiteAnalysisJob)
            .where(SiteAnalysisJob.site_id == site_id)
            .order_by(SiteAnalysisJob.seq.desc())
            .limit(1)
        )
    )
    return _job(result.scalars().first())


async def open_job(
    db: AsyncSession, user_id: str, site_id: str, trigger: str
) -> AnalysisJobRecord | None:
    now = datetime.now(UTC)
    stmt = (
        pg_insert(SiteAnalysisJob)
        .values(
            id=uid("saj"),
            user_id=user_id,
            site_id=site_id,
            status="queued",
            trigger=trigger,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing()
        .returning(SiteAnalysisJob.id)
    )
    job_id = (await db.execute(stmt)).scalar_one_or_none()
    await db.flush()
    return await job_by_id(db, job_id) if job_id else None


async def start_job(db: AsyncSession, job_id: str, total: int) -> bool:
    now = datetime.now(UTC)
    result = await db.execute(
        update(SiteAnalysisJob)
        .where(SiteAnalysisJob.id == job_id, SiteAnalysisJob.status == "queued")
        .values(status="running", total=total, started_at=now, heartbeat_at=now, updated_at=now)
        .returning(SiteAnalysisJob.id)
    )
    await db.flush()
    return result.scalar_one_or_none() is not None


async def beat_job(db: AsyncSession, job_id: str, counters: dict[str, int]) -> None:
    now = datetime.now(UTC)
    await db.execute(
        update(SiteAnalysisJob)
        .where(SiteAnalysisJob.id == job_id)
        .values(**counters, heartbeat_at=now, updated_at=now)
    )
    await db.flush()


async def request_job_stop(
    db: AsyncSession, site_id: str, job_id: str, reason: str
) -> AnalysisJobRecord | None:
    now = datetime.now(UTC)
    result = await db.execute(
        update(SiteAnalysisJob)
        .where(SiteAnalysisJob.site_id == site_id, SiteAnalysisJob.id == job_id, _active())
        .values(
            status=case((SiteAnalysisJob.status == "queued", "cancelled"), else_="cancelling"),
            finished_at=case((SiteAnalysisJob.status == "queued", now), else_=null()),
            stop_reason=reason,
            updated_at=now,
        )
        .returning(SiteAnalysisJob.id)
    )
    stopped = result.scalar_one_or_none()
    await db.flush()
    return await job_by_id(db, stopped) if stopped else None


async def stop_requested(db: AsyncSession, job_id: str) -> bool:
    result = await db.execute(
        select(SiteAnalysisJob.status).where(SiteAnalysisJob.id == job_id).limit(1)
    )
    status = result.scalar_one_or_none()
    return status is None or status in ("cancelling", "cancelled")


async def settle_job(
    db: AsyncSession, job_id: str, status: str, values: dict[str, int | str]
) -> AnalysisJobRecord | None:
    now = datetime.now(UTC)
    result = await db.execute(
        update(SiteAnalysisJob)
        .where(SiteAnalysisJob.id == job_id)
        .values(**values, status=status, finished_at=now, updated_at=now)
        .returning(SiteAnalysisJob.id)
    )
    settled = result.scalar_one_or_none()
    await db.flush()
    return await job_by_id(db, settled) if settled else None


async def reap_stalled_jobs(
    db: AsyncSession, stale_ms: float, reason: str, site_ids: list[str] | None = None
) -> list[AnalysisJobRecord]:
    now = datetime.now(UTC)
    cutoff = now - timedelta(milliseconds=stale_ms)
    conds = [
        _active(),
        func.coalesce(
            SiteAnalysisJob.heartbeat_at, SiteAnalysisJob.started_at, SiteAnalysisJob.created_at
        )
        < cutoff,
    ]
    if site_ids:
        conds.append(SiteAnalysisJob.site_id.in_(site_ids))

    result = await db.execute(
        update(SiteAnalysisJob)
        .where(*conds)
        .values(status="failed", error=reason, stop_reason=reason, finished_at=now, updated_at=now)
        .returning(SiteAnalysisJob.id)
    )
    ids = [row[0] for row in result.all()]
    await db.flush()
    if not ids:
        return []
    rows = (
        (await db.execute(_fresh(select(SiteAnalysisJob).where(SiteAnalysisJob.id.in_(ids)))))
        .scalars()
        .all()
    )
    return [AnalysisJobRecord.model_validate(row) for row in rows]


def _eligible():
    return (
        SitePage.status == 200,
        SitePage.body_text.is_not(None),
        SitePage.body_text != "",
    )


async def candidates(db: AsyncSession, site_id: str) -> list[AnalysisCandidateRecord]:
    result = await db.execute(
        select(
            SitePage.id.label("page_id"),
            SitePage.url,
            SitePage.content_hash,
            SitePageAnalysis.analyzed_from_hash,
        )
        .join(SitePageAnalysis, SitePageAnalysis.page_id == SitePage.id, isouter=True)
        .where(SitePage.site_id == site_id, *_eligible())
        .order_by(SitePage.seq)
    )
    return [AnalysisCandidateRecord.model_validate(row) for row in result.all()]


async def page_exists(db: AsyncSession, site_id: str, page_id: str) -> bool:
    result = await db.execute(
        select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id == page_id).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def upsert_analysis(
    db: AsyncSession, user_id: str, site_id: str, body: PageAnalysisCreateRequest
) -> PageAnalysisRecord:
    now = datetime.now(UTC)
    topics = [t.model_dump() for t in body.topics]
    stmt = (
        pg_insert(SitePageAnalysis)
        .values(
            id=uid("spa"),
            user_id=user_id,
            site_id=site_id,
            page_id=body.page_id,
            topics=topics,
            keywords=body.keywords,
            questions_answered=body.questions_answered,
            analyzed_from_hash=body.analyzed_from_hash,
            analyzed_text=body.analyzed_text,
            model=body.model,
            analyzed_at=now,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=[SitePageAnalysis.page_id],
            set_={
                "topics": topics,
                "keywords": body.keywords,
                "questions_answered": body.questions_answered,
                "analyzed_from_hash": body.analyzed_from_hash,
                "analyzed_text": body.analyzed_text,
                "model": body.model,
                "analyzed_at": now,
                "updated_at": now,
            },
        )
        .returning(SitePageAnalysis.id)
    )
    saved = (await db.execute(stmt)).scalar_one()
    await db.flush()
    return await _analysis_by_id(db, saved)


async def _analysis_by_id(db: AsyncSession, analysis_id: str) -> PageAnalysisRecord:
    result = await db.execute(
        _fresh(select(SitePageAnalysis).where(SitePageAnalysis.id == analysis_id).limit(1))
    )
    return PageAnalysisRecord.model_validate(result.scalars().one())


async def refresh_hash(
    db: AsyncSession, site_id: str, page_id: str, analyzed_from_hash: str | None
) -> PageAnalysisRecord | None:
    result = await db.execute(
        update(SitePageAnalysis)
        .where(SitePageAnalysis.site_id == site_id, SitePageAnalysis.page_id == page_id)
        .values(analyzed_from_hash=analyzed_from_hash, updated_at=datetime.now(UTC))
        .returning(SitePageAnalysis.id)
    )
    refreshed = result.scalar_one_or_none()
    await db.flush()
    return await _analysis_by_id(db, refreshed) if refreshed else None


async def get_analysis(db: AsyncSession, site_id: str, page_id: str) -> PageAnalysisRecord | None:
    result = await db.execute(
        select(SitePageAnalysis)
        .where(SitePageAnalysis.site_id == site_id, SitePageAnalysis.page_id == page_id)
        .limit(1)
    )
    row = result.scalars().first()
    return None if row is None else PageAnalysisRecord.model_validate(row)


async def analysis_counts(db: AsyncSession, site_id: str) -> AnalysisCountsRecord:
    analyzed = (
        await db.execute(
            select(func.count())
            .select_from(SitePageAnalysis)
            .where(SitePageAnalysis.site_id == site_id)
        )
    ).scalar_one()
    eligible = (
        await db.execute(
            select(func.count())
            .select_from(SitePage)
            .where(SitePage.site_id == site_id, *_eligible())
        )
    ).scalar_one()
    return AnalysisCountsRecord(analyzed=analyzed, eligible=eligible)
