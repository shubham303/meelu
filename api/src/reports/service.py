from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.reports.repository import reports
from src.reports.schemas import (
    ReportCreateRequest,
    ReportRecord,
    ReportSummaryRecord,
    ReportUpdateRequest,
)


class ReportService:
    async def list_reports(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        paging: PaginationParams,
        desk: str | None = None,
        search: str | None = None,
    ) -> PaginatedApiResponse[ReportSummaryRecord]:
        return await reports.page_summaries(db, user_id, site_id, desk, search, paging)

    async def create_report(
        self, db: AsyncSession, user_id: str, site_id: str, body: ReportCreateRequest
    ) -> ReportRecord:
        return await reports.create(
            db, user_id, site_id, body.desk, body.title, body.html, body.created_by
        )

    async def get_report(
        self, db: AsyncSession, user_id: str, site_id: str, report_id: str
    ) -> ReportRecord:
        record = await reports.get(db, user_id, site_id, report_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    async def update_report(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        report_id: str,
        body: ReportUpdateRequest,
    ) -> ReportRecord:
        values = body.changes()
        if not values:
            raise HTTPException(400, "Nothing to update — send `title` and/or `html`.")
        record = await self.get_report(db, user_id, site_id, report_id)
        return await reports.update(db, record.id, values)

    async def delete_report(
        self, db: AsyncSession, user_id: str, site_id: str, report_id: str
    ) -> ReportRecord:
        record = await self.get_report(db, user_id, site_id, report_id)
        await reports.delete(db, record.id)
        return record


report_service = ReportService()
