from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models.analytics_reports import AnalyticsReport
from src.analytics.models.analytics_sessions import AnalyticsSession
from src.analytics.models.analytics_sources import AnalyticsSource
from src.analytics.schemas import (
    AnalyticsReportRecord,
    AnalyticsReportSummaryRecord,
    AnalyticsSessionRecord,
    AnalyticsSourceRecord,
)
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService

REPORT_SUMMARY_COLUMNS = (
    AnalyticsReport.id,
    AnalyticsReport.user_id,
    AnalyticsReport.site_id,
    AnalyticsReport.session_id,
    AnalyticsReport.title,
    AnalyticsReport.created_by,
    AnalyticsReport.created_at,
    AnalyticsReport.updated_at,
    func.octet_length(AnalyticsReport.html).label("html_bytes"),
)


def _sessions_query(user_id: str, site_id: str):
    return (
        select(AnalyticsSession)
        .where(AnalyticsSession.user_id == user_id, AnalyticsSession.site_id == site_id)
        .order_by(AnalyticsSession.seq.desc())
    )


async def list_sessions(
    db: AsyncSession, user_id: str, site_id: str
) -> list[AnalyticsSessionRecord]:
    rows = (await db.execute(_sessions_query(user_id, site_id))).scalars().all()
    return [AnalyticsSessionRecord.model_validate(r) for r in rows]


async def page_sessions(
    db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[AnalyticsSessionRecord]:
    return await PaginationService.paginate_query(
        db, _sessions_query(user_id, site_id), paging.page, paging.page_size, AnalyticsSessionRecord
    )


async def count_sessions(db: AsyncSession, user_id: str, site_id: str) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(AnalyticsSession)
            .where(AnalyticsSession.user_id == user_id, AnalyticsSession.site_id == site_id)
        )
    ).scalar_one()


async def get_session(
    db: AsyncSession, user_id: str, site_id: str, session_id: str
) -> AnalyticsSessionRecord | None:
    row = (
        await db.execute(
            select(AnalyticsSession).where(
                AnalyticsSession.user_id == user_id,
                AnalyticsSession.site_id == site_id,
                AnalyticsSession.id == session_id,
            )
        )
    ).scalar_one_or_none()
    return None if row is None else AnalyticsSessionRecord.model_validate(row)


async def create_session(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    title: str,
    about: str,
    session_key: str | None,
) -> AnalyticsSessionRecord:
    now = datetime.now(UTC)
    row = AnalyticsSession(
        id=uid("ssn"),
        user_id=user_id,
        site_id=site_id,
        title=title,
        about=about,
        session_key=session_key,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return AnalyticsSessionRecord.model_validate(row)


async def update_session(
    db: AsyncSession, session_id: str, values: dict[str, Any]
) -> AnalyticsSessionRecord:
    row = (
        await db.execute(
            update(AnalyticsSession)
            .where(AnalyticsSession.id == session_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(AnalyticsSession)
        )
    ).scalar_one()
    return AnalyticsSessionRecord.model_validate(row)


async def delete_session_reports(db: AsyncSession, session_id: str) -> None:
    await db.execute(delete(AnalyticsReport).where(AnalyticsReport.session_id == session_id))
    await db.flush()


async def delete_session(db: AsyncSession, session_id: str) -> None:
    await db.execute(delete(AnalyticsSession).where(AnalyticsSession.id == session_id))
    await db.flush()


def _sources_query(user_id: str, site_id: str, session_id: str | None = None):
    query = select(AnalyticsSource).where(
        AnalyticsSource.user_id == user_id, AnalyticsSource.site_id == site_id
    )
    if session_id is not None:
        query = query.where(AnalyticsSource.session_id == session_id)
    return query.order_by(AnalyticsSource.seq.desc())


async def list_sources(db: AsyncSession, user_id: str, site_id: str) -> list[AnalyticsSourceRecord]:
    rows = (await db.execute(_sources_query(user_id, site_id))).scalars().all()
    return [AnalyticsSourceRecord.model_validate(r) for r in rows]


async def page_session_sources(
    db: AsyncSession, user_id: str, site_id: str, session_id: str, paging: PaginationParams
) -> PaginatedApiResponse[AnalyticsSourceRecord]:
    return await PaginationService.paginate_query(
        db,
        _sources_query(user_id, site_id, session_id),
        paging.page,
        paging.page_size,
        AnalyticsSourceRecord,
    )


async def get_source(
    db: AsyncSession, user_id: str, site_id: str, source_id: str
) -> AnalyticsSourceRecord | None:
    row = (
        await db.execute(
            select(AnalyticsSource).where(
                AnalyticsSource.user_id == user_id,
                AnalyticsSource.site_id == site_id,
                AnalyticsSource.id == source_id,
            )
        )
    ).scalar_one_or_none()
    return None if row is None else AnalyticsSourceRecord.model_validate(row)


async def create_source(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    session_id: str,
    name: str,
    file_path: str | None,
) -> AnalyticsSourceRecord:
    now = datetime.now(UTC)
    row = AnalyticsSource(
        id=uid("dsrc"),
        user_id=user_id,
        site_id=site_id,
        session_id=session_id,
        name=name,
        file_path=file_path,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return AnalyticsSourceRecord.model_validate(row)


async def delete_source(db: AsyncSession, source_id: str) -> None:
    await db.execute(delete(AnalyticsSource).where(AnalyticsSource.id == source_id))
    await db.flush()


def _report_conditions(user_id: str, site_id: str, session_id: str | None):
    conds = [AnalyticsReport.user_id == user_id, AnalyticsReport.site_id == site_id]
    if session_id:
        conds.append(AnalyticsReport.session_id == session_id)
    return conds


async def list_report_summaries(
    db: AsyncSession, user_id: str, site_id: str, session_id: str | None = None
) -> list[AnalyticsReportSummaryRecord]:
    result = await db.execute(
        select(*REPORT_SUMMARY_COLUMNS)
        .where(*_report_conditions(user_id, site_id, session_id))
        .order_by(AnalyticsReport.seq.desc())
    )
    return [AnalyticsReportSummaryRecord.model_validate(row) for row in result.mappings().all()]


async def page_report_summaries(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    session_id: str | None,
    paging: PaginationParams,
) -> PaginatedApiResponse[AnalyticsReportSummaryRecord]:
    conds = _report_conditions(user_id, site_id, session_id)
    total = (
        await db.execute(select(func.count()).select_from(AnalyticsReport).where(*conds))
    ).scalar_one()
    result = await db.execute(
        select(*REPORT_SUMMARY_COLUMNS)
        .where(*conds)
        .order_by(AnalyticsReport.seq.desc())
        .offset(paging.offset)
        .limit(paging.page_size)
    )
    return PaginatedApiResponse[AnalyticsReportSummaryRecord](
        data=[AnalyticsReportSummaryRecord.model_validate(row) for row in result.mappings().all()],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def get_report(
    db: AsyncSession, user_id: str, site_id: str, report_id: str
) -> AnalyticsReportRecord | None:
    row = (
        await db.execute(
            select(AnalyticsReport).where(
                AnalyticsReport.user_id == user_id,
                AnalyticsReport.site_id == site_id,
                AnalyticsReport.id == report_id,
            )
        )
    ).scalar_one_or_none()
    return None if row is None else AnalyticsReportRecord.model_validate(row)


async def create_report(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    session_id: str | None,
    title: str,
    html: str,
    created_by: str,
) -> AnalyticsReportRecord:
    now = datetime.now(UTC)
    row = AnalyticsReport(
        id=uid("rpt"),
        user_id=user_id,
        site_id=site_id,
        session_id=session_id,
        title=title,
        html=html,
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return AnalyticsReportRecord.model_validate(row)


async def update_report(
    db: AsyncSession, report_id: str, values: dict[str, Any]
) -> AnalyticsReportRecord:
    row = (
        await db.execute(
            update(AnalyticsReport)
            .where(AnalyticsReport.id == report_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(AnalyticsReport)
        )
    ).scalar_one()
    return AnalyticsReportRecord.model_validate(row)


async def delete_report(db: AsyncSession, report_id: str) -> None:
    await db.execute(delete(AnalyticsReport).where(AnalyticsReport.id == report_id))
    await db.flush()
