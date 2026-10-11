from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models.analytics_reports import AnalyticsReport
from src.analytics.schemas import AnalyticsReportRecord, AnalyticsReportSummaryRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService

SUMMARY_COLUMNS = (
    AnalyticsReport.id,
    AnalyticsReport.user_id,
    AnalyticsReport.site_id,
    AnalyticsReport.title,
    AnalyticsReport.created_by,
    AnalyticsReport.created_at,
    AnalyticsReport.updated_at,
    func.octet_length(AnalyticsReport.html).label("html_bytes"),
)


class AnalyticsReportRepository:
    async def page_summaries(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        search: str | None,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[AnalyticsReportSummaryRecord]:
        conds = self._conditions(user_id, site_id, search)
        total = (
            await db.execute(select(func.count()).select_from(AnalyticsReport).where(*conds))
        ).scalar_one()
        result = await db.execute(
            select(*SUMMARY_COLUMNS)
            .where(*conds)
            .order_by(AnalyticsReport.seq.desc())
            .offset(paging.offset)
            .limit(paging.page_size)
        )
        return PaginatedApiResponse[AnalyticsReportSummaryRecord](
            data=[
                AnalyticsReportSummaryRecord.model_validate(row) for row in result.mappings().all()
            ],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, report_id: str
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

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        title: str,
        html: str,
        created_by: str,
    ) -> AnalyticsReportRecord:
        now = datetime.now(UTC)
        row = AnalyticsReport(
            id=uid("rpt"),
            user_id=user_id,
            site_id=site_id,
            title=title,
            html=html,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return AnalyticsReportRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, report_id: str, values: dict[str, Any]
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

    async def delete(self, db: AsyncSession, report_id: str) -> None:
        await db.execute(delete(AnalyticsReport).where(AnalyticsReport.id == report_id))
        await db.flush()

    def _conditions(self, user_id: str, site_id: str, search: str | None) -> list[Any]:
        conds: list[Any] = [AnalyticsReport.user_id == user_id, AnalyticsReport.site_id == site_id]
        if search:
            conds.append(AnalyticsReport.title.ilike(f"%{search}%"))
        return conds


analytics_reports = AnalyticsReportRepository()
