from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics import repository as repo
from src.analytics.schemas import (
    AnalyticsReportCreateRequest,
    AnalyticsReportRecord,
    AnalyticsReportSummaryRecord,
    AnalyticsReportUpdateRequest,
    AnalyticsSessionCreateRequest,
    AnalyticsSessionRecord,
    AnalyticsSessionUpdateRequest,
    AnalyticsSourceCreateRequest,
    AnalyticsSourceRecord,
    AnalyticsWorkspaceResult,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams


async def list_sessions(
    db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[AnalyticsSessionRecord]:
    return await repo.page_sessions(db, user_id, site_id, paging)


async def get_session(
    db: AsyncSession, user_id: str, site_id: str, session_id: str
) -> AnalyticsSessionRecord:
    record = await repo.get_session(db, user_id, site_id, session_id)
    if record is None:
        raise HTTPException(404, "Not found")
    return record


async def create_session(
    db: AsyncSession, user_id: str, site_id: str, body: AnalyticsSessionCreateRequest
) -> AnalyticsSessionRecord:
    title = body.title
    if title is None:
        title = f"Session {await repo.count_sessions(db, user_id, site_id) + 1}"
    return await repo.create_session(db, user_id, site_id, title, body.about, body.session_key)


async def update_session(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    session_id: str,
    body: AnalyticsSessionUpdateRequest,
) -> AnalyticsSessionRecord:
    values = body.changes()
    if not values:
        raise HTTPException(400, "Nothing to update — send `title`, `about` and/or `sessionKey`.")
    record = await get_session(db, user_id, site_id, session_id)
    return await repo.update_session(db, record.id, values)


async def delete_session(
    db: AsyncSession, user_id: str, site_id: str, session_id: str
) -> AnalyticsSessionRecord:
    record = await get_session(db, user_id, site_id, session_id)
    await repo.delete_session_reports(db, record.id)
    await repo.delete_session(db, record.id)
    return record


async def list_sources(
    db: AsyncSession, user_id: str, site_id: str, session_id: str, paging: PaginationParams
) -> PaginatedApiResponse[AnalyticsSourceRecord]:
    await get_session(db, user_id, site_id, session_id)
    return await repo.page_session_sources(db, user_id, site_id, session_id, paging)


async def create_source(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    session_id: str,
    body: AnalyticsSourceCreateRequest,
) -> AnalyticsSourceRecord:
    session = await get_session(db, user_id, site_id, session_id)
    return await repo.create_source(db, user_id, site_id, session.id, body.name, body.file_path)


async def delete_source(
    db: AsyncSession, user_id: str, site_id: str, source_id: str
) -> AnalyticsSourceRecord:
    record = await repo.get_source(db, user_id, site_id, source_id)
    if record is None:
        raise HTTPException(404, "Not found")
    await repo.delete_source(db, record.id)
    return record


async def list_reports(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    session_id: str | None = None,
) -> PaginatedApiResponse[AnalyticsReportSummaryRecord]:
    return await repo.page_report_summaries(db, user_id, site_id, session_id, paging)


async def create_report(
    db: AsyncSession, user_id: str, site_id: str, body: AnalyticsReportCreateRequest
) -> AnalyticsReportRecord:
    session_id = None
    if body.session_id is not None:
        session_id = (await get_session(db, user_id, site_id, body.session_id)).id
    return await repo.create_report(
        db, user_id, site_id, session_id, body.title, body.html, body.created_by
    )


async def get_report(
    db: AsyncSession, user_id: str, site_id: str, report_id: str
) -> AnalyticsReportRecord:
    record = await repo.get_report(db, user_id, site_id, report_id)
    if record is None:
        raise HTTPException(404, "Not found")
    return record


async def update_report(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    report_id: str,
    body: AnalyticsReportUpdateRequest,
) -> AnalyticsReportRecord:
    values = body.changes()
    if not values:
        raise HTTPException(400, "Nothing to update — send `title` and/or `html`.")
    record = await get_report(db, user_id, site_id, report_id)
    return await repo.update_report(db, record.id, values)


async def delete_report(
    db: AsyncSession, user_id: str, site_id: str, report_id: str
) -> AnalyticsReportRecord:
    record = await get_report(db, user_id, site_id, report_id)
    await repo.delete_report(db, record.id)
    return record


async def get_workspace(db: AsyncSession, user_id: str, site_id: str) -> AnalyticsWorkspaceResult:
    return AnalyticsWorkspaceResult(
        sessions=await repo.list_sessions(db, user_id, site_id),
        sources=await repo.list_sources(db, user_id, site_id),
        reports=await repo.list_report_summaries(db, user_id, site_id),
    )
