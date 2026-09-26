from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.technical_seo.service import technical_seo_service
from src.technical_seo.filters import (
    audit_run_filter,
    default_open_state,
    optional_kinds,
    page_issue_filter,
    site_issue_filter,
)
from src.technical_seo.schemas import (
    AuditResultResponse,
    AuditRunDeleteResponse,
    AuditRunFilter,
    AuditRunListItemResponse,
    AuditRunResponse,
    AuditRunUpdateRequest,
    AuditStartRequest,
    AuditSummaryResponse,
    IssueBulkUpdateResult,
    IssueGroupResponse,
    IssueUpdateRequest,
    PageIssueBulkUpdateRequest,
    PageIssueCreateRequest,
    PageIssueDeleteResponse,
    PageIssueFilter,
    PageIssueListItemResponse,
    PageIssueResponse,
    SiteIssueBulkUpdateRequest,
    SiteIssueCreateRequest,
    SiteIssueDeleteResponse,
    SiteIssueFilter,
    SiteIssueListItemResponse,
    SiteIssueResponse,
)

router = APIRouter(prefix="/site/technical-seo")


@router.get("/runs")
async def list_runs(
    filters: AuditRunFilter = Depends(audit_run_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[AuditRunListItemResponse]:
    page = await technical_seo_service.list_runs(db, ctx.site_id, filters, paging)
    return PaginatedApiResponse[AuditRunListItemResponse](
        data=[AuditRunListItemResponse.model_validate(r) for r in page.data],
        pagination=page.pagination,
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AuditRunResponse:
    return AuditRunResponse.model_validate(
        await technical_seo_service.get_run(db, ctx.site_id, run_id)
    )


@router.put("/runs/{run_id}")
@router.patch("/runs/{run_id}")
async def update_run(
    run_id: str,
    body: AuditRunUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AuditRunResponse:
    return AuditRunResponse.model_validate(
        await technical_seo_service.update_run(db, ctx.site_id, run_id, body)
    )


@router.delete("/runs/{run_id}")
async def delete_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AuditRunDeleteResponse:
    run = await technical_seo_service.delete_run(db, ctx.site_id, run_id)
    return AuditRunDeleteResponse(id=run.id)


@router.post("/run-audit", status_code=201)
async def run_audit(
    body: AuditStartRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AuditResultResponse:
    return await technical_seo_service.run_audit(db, ctx.user_id, ctx.site_id, body)


@router.get("/issues")
async def list_site_issues(
    run_id: str | None = Query(None, alias="runId"),
    filters: SiteIssueFilter = Depends(site_issue_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[SiteIssueListItemResponse]:
    page = await technical_seo_service.list_site_issues(db, ctx.site_id, run_id, filters, paging)
    return PaginatedApiResponse[SiteIssueListItemResponse](
        data=[SiteIssueListItemResponse.model_validate(i) for i in page.data],
        pagination=page.pagination,
    )


@router.post("/issues", status_code=201)
async def create_site_issue(
    body: SiteIssueCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteIssueResponse:
    record = await technical_seo_service.create_site_issue(db, ctx.user_id, ctx.site_id, body)
    return SiteIssueResponse.model_validate(record)


@router.patch("/issues")
async def patch_site_issues(
    body: SiteIssueBulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> IssueBulkUpdateResult:
    return await technical_seo_service.update_site_issues_by_kind(db, ctx.site_id, body)


@router.get("/issues/{issue_id}")
async def get_site_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteIssueResponse:
    return SiteIssueResponse.model_validate(
        await technical_seo_service.get_site_issue(db, ctx.site_id, issue_id)
    )


@router.put("/issues/{issue_id}")
@router.patch("/issues/{issue_id}")
async def update_site_issue(
    issue_id: str,
    body: IssueUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteIssueResponse:
    record = await technical_seo_service.update_site_issue(db, ctx.site_id, issue_id, body)
    return SiteIssueResponse.model_validate(record)


@router.delete("/issues/{issue_id}")
async def delete_site_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteIssueDeleteResponse:
    record = await technical_seo_service.delete_site_issue(db, ctx.site_id, issue_id)
    return SiteIssueDeleteResponse(id=record.id)


@router.get("/page-issues")
async def list_page_issues(
    run_id: str | None = Query(None, alias="runId"),
    filters: PageIssueFilter = Depends(page_issue_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PageIssueListItemResponse]:
    page = await technical_seo_service.list_page_issues(db, ctx.site_id, run_id, filters, paging)
    return PaginatedApiResponse[PageIssueListItemResponse](
        data=[PageIssueListItemResponse.model_validate(i) for i in page.data],
        pagination=page.pagination,
    )


@router.post("/page-issues", status_code=201)
async def create_page_issue(
    body: PageIssueCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageIssueResponse:
    record = await technical_seo_service.create_page_issue(db, ctx.user_id, ctx.site_id, body)
    return PageIssueResponse.model_validate(record)


@router.patch("/page-issues")
async def patch_page_issues(
    body: PageIssueBulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> IssueBulkUpdateResult:
    return await technical_seo_service.update_page_issues_by(db, ctx.site_id, body)


@router.get("/page-issues/{issue_id}")
async def get_page_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageIssueResponse:
    return PageIssueResponse.model_validate(
        await technical_seo_service.get_page_issue(db, ctx.site_id, issue_id)
    )


@router.put("/page-issues/{issue_id}")
@router.patch("/page-issues/{issue_id}")
async def update_page_issue(
    issue_id: str,
    body: IssueUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageIssueResponse:
    record = await technical_seo_service.update_page_issue(db, ctx.site_id, issue_id, body)
    return PageIssueResponse.model_validate(record)


@router.delete("/page-issues/{issue_id}")
async def delete_page_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageIssueDeleteResponse:
    record = await technical_seo_service.delete_page_issue(db, ctx.site_id, issue_id)
    return PageIssueDeleteResponse(id=record.id)


@router.get("/groups")
async def list_groups(
    run_id: str | None = Query(None, alias="runId"),
    state: str = Depends(default_open_state),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[IssueGroupResponse]:
    return await technical_seo_service.list_groups(db, ctx.site_id, run_id, state)


@router.get("/summary")
async def summary(
    run_id: str | None = Query(None, alias="runId"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> AuditSummaryResponse:
    return await technical_seo_service.summary(db, ctx.site_id, run_id)


@router.get("/download")
async def download(
    run_id: str | None = Query(None, alias="runId"),
    state: str = Depends(default_open_state),
    kinds: list[str] | None = Depends(optional_kinds),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> Response:
    file = await technical_seo_service.csv(db, ctx.user_id, ctx.site_id, run_id, state, kinds)
    return Response(
        content=file.body,
        headers={
            "content-type": "text/csv; charset=utf-8",
            "content-disposition": f'attachment; filename="{file.filename}"',
            "cache-control": "no-store",
        },
    )
