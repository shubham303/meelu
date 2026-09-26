from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.repositories.reports import analytics_reports
from src.analytics.repositories.sessions import analytics_sessions
from src.analytics.repositories.sources import analytics_sources
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


class AnalyticsService:
    async def list_sessions(
        self, db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AnalyticsSessionRecord]:
        return await analytics_sessions.page(db, user_id, site_id, paging)

    async def get_session(
        self, db: AsyncSession, user_id: str, site_id: str, session_id: str
    ) -> AnalyticsSessionRecord:
        record = await analytics_sessions.get(db, user_id, site_id, session_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    async def create_session(
        self, db: AsyncSession, user_id: str, site_id: str, body: AnalyticsSessionCreateRequest
    ) -> AnalyticsSessionRecord:
        title = body.title
        if title is None:
            title = f"Session {await analytics_sessions.count(db, user_id, site_id) + 1}"
        return await analytics_sessions.create(
            db, user_id, site_id, title, body.about, body.session_key
        )

    async def update_session(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        session_id: str,
        body: AnalyticsSessionUpdateRequest,
    ) -> AnalyticsSessionRecord:
        values = body.changes()
        if not values:
            raise HTTPException(
                400, "Nothing to update — send `title`, `about` and/or `sessionKey`."
            )
        record = await self.get_session(db, user_id, site_id, session_id)
        return await analytics_sessions.update(db, record.id, values)

    async def delete_session(
        self, db: AsyncSession, user_id: str, site_id: str, session_id: str
    ) -> AnalyticsSessionRecord:
        record = await self.get_session(db, user_id, site_id, session_id)
        await analytics_reports.delete_by_session(db, record.id)
        await analytics_sessions.delete(db, record.id)
        return record

    async def list_sources(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        session_id: str,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[AnalyticsSourceRecord]:
        await self.get_session(db, user_id, site_id, session_id)
        return await analytics_sources.page_by_session(db, user_id, site_id, session_id, paging)

    async def create_source(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        session_id: str,
        body: AnalyticsSourceCreateRequest,
    ) -> AnalyticsSourceRecord:
        session = await self.get_session(db, user_id, site_id, session_id)
        return await analytics_sources.create(
            db, user_id, site_id, session.id, body.name, body.file_path
        )

    async def delete_source(
        self, db: AsyncSession, user_id: str, site_id: str, source_id: str
    ) -> AnalyticsSourceRecord:
        record = await analytics_sources.get(db, user_id, site_id, source_id)
        if record is None:
            raise HTTPException(404, "Not found")
        await analytics_sources.delete(db, record.id)
        return record

    async def list_reports(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        paging: PaginationParams,
        session_id: str | None = None,
    ) -> PaginatedApiResponse[AnalyticsReportSummaryRecord]:
        return await analytics_reports.page_summaries(db, user_id, site_id, session_id, paging)

    async def create_report(
        self, db: AsyncSession, user_id: str, site_id: str, body: AnalyticsReportCreateRequest
    ) -> AnalyticsReportRecord:
        session_id = None
        if body.session_id is not None:
            session_id = (await self.get_session(db, user_id, site_id, body.session_id)).id
        return await analytics_reports.create(
            db, user_id, site_id, session_id, body.title, body.html, body.created_by
        )

    async def get_report(
        self, db: AsyncSession, user_id: str, site_id: str, report_id: str
    ) -> AnalyticsReportRecord:
        record = await analytics_reports.get(db, user_id, site_id, report_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    async def update_report(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        report_id: str,
        body: AnalyticsReportUpdateRequest,
    ) -> AnalyticsReportRecord:
        values = body.changes()
        if not values:
            raise HTTPException(400, "Nothing to update — send `title` and/or `html`.")
        record = await self.get_report(db, user_id, site_id, report_id)
        return await analytics_reports.update(db, record.id, values)

    async def delete_report(
        self, db: AsyncSession, user_id: str, site_id: str, report_id: str
    ) -> AnalyticsReportRecord:
        record = await self.get_report(db, user_id, site_id, report_id)
        await analytics_reports.delete(db, record.id)
        return record

    async def get_workspace(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> AnalyticsWorkspaceResult:
        return AnalyticsWorkspaceResult(
            sessions=await analytics_sessions.list_all(db, user_id, site_id),
            sources=await analytics_sources.list_all(db, user_id, site_id),
            reports=await analytics_reports.list_summaries(db, user_id, site_id),
        )


analytics_service = AnalyticsService()
