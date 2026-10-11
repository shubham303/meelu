from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.schemas import (
    AnalyticsChatCreateRequest,
    AnalyticsChatDeleteResponse,
    AnalyticsChatListItemResponse,
    AnalyticsChatMessageResponse,
    AnalyticsChatMessagesCreateRequest,
    AnalyticsChatResponse,
    AnalyticsChatUpdateRequest,
    AnalyticsReportCreateRequest,
    AnalyticsReportDeleteResponse,
    AnalyticsReportListItemResponse,
    AnalyticsReportResponse,
    AnalyticsReportSummaryRecord,
    AnalyticsReportSummaryResponse,
    AnalyticsReportUpdateRequest,
)
from src.analytics.service import analytics_service
from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params

router = APIRouter()


@router.get("/analytics/reports")
async def list_reports(
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AnalyticsReportListItemResponse]:
    page = await analytics_service.list_reports(db, ctx.user_id, ctx.site_id, paging, q)
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


@router.get("/analytics/chats")
async def list_chats(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AnalyticsChatListItemResponse]:
    page = await analytics_service.list_chats(db, ctx.user_id, ctx.site_id, paging)
    return PaginatedApiResponse[AnalyticsChatListItemResponse](
        data=[AnalyticsChatListItemResponse.model_validate(c) for c in page.data],
        pagination=page.pagination,
    )


@router.post("/analytics/chats", status_code=201)
async def create_chat(
    body: AnalyticsChatCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsChatResponse:
    record = await analytics_service.create_chat(db, ctx.user_id, ctx.site_id, body)
    return AnalyticsChatResponse.model_validate(record)


@router.get("/analytics/chats/{chat_id}")
async def get_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsChatResponse:
    record = await analytics_service.get_chat(db, ctx.user_id, ctx.site_id, chat_id)
    return AnalyticsChatResponse.model_validate(record)


@router.put("/analytics/chats/{chat_id}")
async def update_chat(
    chat_id: str,
    body: AnalyticsChatUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsChatResponse:
    record = await analytics_service.update_chat(db, ctx.user_id, ctx.site_id, chat_id, body)
    return AnalyticsChatResponse.model_validate(record)


@router.delete("/analytics/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AnalyticsChatDeleteResponse:
    record = await analytics_service.delete_chat(db, ctx.user_id, ctx.site_id, chat_id)
    return AnalyticsChatDeleteResponse(id=record.id)


@router.get("/analytics/chats/{chat_id}/messages")
async def list_messages(
    chat_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AnalyticsChatMessageResponse]:
    page = await analytics_service.list_messages(db, ctx.user_id, ctx.site_id, chat_id, paging)
    return PaginatedApiResponse[AnalyticsChatMessageResponse](
        data=[AnalyticsChatMessageResponse.model_validate(m) for m in page.data],
        pagination=page.pagination,
    )


@router.post("/analytics/chats/{chat_id}/messages", status_code=201)
async def add_messages(
    chat_id: str,
    body: AnalyticsChatMessagesCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[AnalyticsChatMessageResponse]:
    records = await analytics_service.add_messages(db, ctx.user_id, ctx.site_id, chat_id, body)
    return [AnalyticsChatMessageResponse.model_validate(m) for m in records]
