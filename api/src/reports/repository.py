from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.reports.models.report import Report
from src.reports.schemas import ReportRecord, ReportSummaryRecord

SUMMARY_COLUMNS = (
    Report.id,
    Report.user_id,
    Report.site_id,
    Report.desk,
    Report.title,
    Report.created_by,
    Report.created_at,
    Report.updated_at,
    func.octet_length(Report.html).label("html_bytes"),
)


class ReportRepository:
    async def page_summaries(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        desk: str | None,
        search: str | None,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[ReportSummaryRecord]:
        conds = self._conditions(user_id, site_id, desk, search)
        total = (
            await db.execute(select(func.count()).select_from(Report).where(*conds))
        ).scalar_one()
        result = await db.execute(
            select(*SUMMARY_COLUMNS)
            .where(*conds)
            .order_by(Report.seq.desc())
            .offset(paging.offset)
            .limit(paging.page_size)
        )
        return PaginatedApiResponse[ReportSummaryRecord](
            data=[ReportSummaryRecord.model_validate(row) for row in result.mappings().all()],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, report_id: str
    ) -> ReportRecord | None:
        row = (
            await db.execute(
                select(Report).where(
                    Report.user_id == user_id,
                    Report.site_id == site_id,
                    Report.id == report_id,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else ReportRecord.model_validate(row)

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        desk: str,
        title: str,
        html: str,
        created_by: str,
    ) -> ReportRecord:
        now = datetime.now(UTC)
        row = Report(
            id=uid("rpt"),
            user_id=user_id,
            site_id=site_id,
            desk=desk,
            title=title,
            html=html,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return ReportRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, report_id: str, values: dict[str, Any]
    ) -> ReportRecord:
        row = (
            await db.execute(
                update(Report)
                .where(Report.id == report_id)
                .values(**values, updated_at=datetime.now(UTC))
                .returning(Report)
            )
        ).scalar_one()
        return ReportRecord.model_validate(row)

    async def delete(self, db: AsyncSession, report_id: str) -> None:
        await db.execute(delete(Report).where(Report.id == report_id))
        await db.flush()

    def _conditions(
        self, user_id: str, site_id: str, desk: str | None, search: str | None
    ) -> list[Any]:
        conds: list[Any] = [Report.user_id == user_id, Report.site_id == site_id]
        if desk:
            conds.append(Report.desk == desk)
        if search:
            conds.append(Report.title.ilike(f"%{search}%"))
        return conds


reports = ReportRepository()
