from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.service import analytics_service
from src.analytics.schemas import (
    AnalyticsReportCreateRequest,
    AnalyticsReportDeleteResponse,
    AnalyticsReportListItemResponse,
    AnalyticsReportResponse,
    AnalyticsReportSummaryRecord,
    AnalyticsReportSummaryResponse,
    AnalyticsReportUpdateRequest,
    AnalyticsSessionCreateRequest,
    AnalyticsSessionDeleteResponse,
    AnalyticsSessionListItemResponse,
    AnalyticsSessionResponse,
    AnalyticsSessionUpdateRequest,
    AnalyticsSourceCreateRequest,
    AnalyticsSourceDeleteResponse,
    AnalyticsSourceListItemResponse,
    AnalyticsSourceResponse,
    AnalyticsWorkspaceResponse,
)
from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params

router = APIRouter()


@router.get("/analytics/workspace")
async def get_workspace(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsWorkspaceResponse:
    workspace = await analytics_service.get_workspace(db, ctx.user_id, ctx.site_id)
    return AnalyticsWorkspaceResponse.model_validate(workspace)


@router.get("/analytics/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AnalyticsSessionListItemResponse]:
    page = await analytics_service.list_sessions(db, ctx.user_id, ctx.site_id, paging)
    return PaginatedApiResponse[AnalyticsSessionListItemResponse](
        data=[AnalyticsSessionListItemResponse.model_validate(s) for s in page.data],
        pagination=page.pagination,
    )


@router.post("/analytics/sessions", status_code=201)
async def create_session(
    body: AnalyticsSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsSessionResponse:
    record = await analytics_service.create_session(db, ctx.user_id, ctx.site_id, body)
    return AnalyticsSessionResponse.model_validate(record)


@router.get("/analytics/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsSessionResponse:
    record = await analytics_service.get_session(db, ctx.user_id, ctx.site_id, session_id)
    return AnalyticsSessionResponse.model_validate(record)


@router.put("/analytics/sessions/{session_id}")
async def update_session(
    session_id: str,
    body: AnalyticsSessionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsSessionResponse:
    record = await analytics_service.update_session(db, ctx.user_id, ctx.site_id, session_id, body)
    return AnalyticsSessionResponse.model_validate(record)


@router.delete("/analytics/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsSessionDeleteResponse:
    record = await analytics_service.delete_session(db, ctx.user_id, ctx.site_id, session_id)
    return AnalyticsSessionDeleteResponse(id=record.id)


@router.get("/analytics/sessions/{session_id}/sources")
async def list_sources(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AnalyticsSourceListItemResponse]:
    page = await analytics_service.list_sources(db, ctx.user_id, ctx.site_id, session_id, paging)
    return PaginatedApiResponse[AnalyticsSourceListItemResponse](
        data=[AnalyticsSourceListItemResponse.model_validate(s) for s in page.data],
        pagination=page.pagination,
    )


@router.post("/analytics/sessions/{session_id}/sources", status_code=201)
async def create_source(
    session_id: str,
    body: AnalyticsSourceCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsSourceResponse:
    record = await analytics_service.create_source(db, ctx.user_id, ctx.site_id, session_id, body)
    return AnalyticsSourceResponse.model_validate(record)


@router.delete("/analytics/sources/{source_id}")
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsSourceDeleteResponse:
    record = await analytics_service.delete_source(db, ctx.user_id, ctx.site_id, source_id)
    return AnalyticsSourceDeleteResponse(id=record.id)


@router.get("/analytics/reports")
async def list_reports(
    session_id: str | None = Query(None, alias="sessionId"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AnalyticsReportListItemResponse]:
    page = await analytics_service.list_reports(db, ctx.user_id, ctx.site_id, paging, session_id)
    return PaginatedApiResponse[AnalyticsReportListItemResponse](
        data=[AnalyticsReportListItemResponse.model_validate(r) for r in page.data],
        pagination=page.pagination,
    )


@router.post("/analytics/reports", status_code=201)
async def create_report(
    body: AnalyticsReportCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsReportSummaryResponse:
    record = await analytics_service.create_report(db, ctx.user_id, ctx.site_id, body)
    return AnalyticsReportSummaryResponse.model_validate(
        AnalyticsReportSummaryRecord.from_report(record)
    )


@router.get("/analytics/reports/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsReportResponse:
    record = await analytics_service.get_report(db, ctx.user_id, ctx.site_id, report_id)
    return AnalyticsReportResponse.model_validate(record)


@router.put("/analytics/reports/{report_id}")
async def update_report(
    report_id: str,
    body: AnalyticsReportUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsReportSummaryResponse:
    record = await analytics_service.update_report(db, ctx.user_id, ctx.site_id, report_id, body)
    return AnalyticsReportSummaryResponse.model_validate(
        AnalyticsReportSummaryRecord.from_report(record)
    )


@router.delete("/analytics/reports/{report_id}")
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsReportDeleteResponse:
    record = await analytics_service.delete_report(db, ctx.user_id, ctx.site_id, report_id)
    return AnalyticsReportDeleteResponse(id=record.id)
