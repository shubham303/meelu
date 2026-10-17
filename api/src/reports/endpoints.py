from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.reports.schemas import (
    ReportCreateRequest,
    ReportDeleteResponse,
    ReportDesk,
    ReportResponse,
    ReportSummaryRecord,
    ReportSummaryResponse,
    ReportUpdateRequest,
)
from src.reports.service import report_service

router = APIRouter()


@router.get("/reports")
async def list_reports(
    q: str | None = Query(None),
    desk: ReportDesk | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[ReportSummaryResponse]:
    page = await report_service.list_reports(db, ctx.user_id, ctx.site_id, paging, desk, q)
    return PaginatedApiResponse[ReportSummaryResponse](
        data=[ReportSummaryResponse.model_validate(r) for r in page.data],
        pagination=page.pagination,
    )


@router.post("/reports", status_code=201)
async def create_report(
    body: ReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReportSummaryResponse:
    record = await report_service.create_report(db, ctx.user_id, ctx.site_id, body)
    return ReportSummaryResponse.model_validate(ReportSummaryRecord.from_report(record))


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReportResponse:
    record = await report_service.get_report(db, ctx.user_id, ctx.site_id, report_id)
    return ReportResponse.model_validate(record)


@router.put("/reports/{report_id}")
async def update_report(
    report_id: str,
    body: ReportUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReportSummaryResponse:
    record = await report_service.update_report(db, ctx.user_id, ctx.site_id, report_id, body)
    return ReportSummaryResponse.model_validate(ReportSummaryRecord.from_report(record))


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReportDeleteResponse:
    record = await report_service.delete_report(db, ctx.user_id, ctx.site_id, report_id)
    return ReportDeleteResponse(id=record.id)
