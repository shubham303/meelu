from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.leads.service import LeadExistsError, lead_service
from src.leads.schemas import (
    BulkLeadsResponse,
    CampaignCreateRequest,
    CampaignPatchRequest,
    CampaignResponse,
    DeleteResponse,
    LeadCreateRequest,
    LeadFilters,
    LeadPatchRequest,
    LeadResponse,
    LeadsBulkRequest,
    RunCreateRequest,
    RunResponse,
    RunUpdateRequest,
    SummaryResponse,
)

router = APIRouter()


@router.get("/lead-management/campaigns")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[CampaignResponse]:
    return await lead_service.list_campaigns(db, ctx.site_id)


@router.post("/lead-management/campaigns", status_code=201)
async def create_campaign(
    body: CampaignCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignResponse:
    return await lead_service.create_campaign(db, ctx.user_id, ctx.site_id, body)


@router.get("/lead-management/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignResponse:
    return await lead_service.get_campaign(db, ctx.site_id, campaign_id)


@router.patch("/lead-management/campaigns/{campaign_id}")
async def patch_campaign(
    campaign_id: str,
    body: CampaignPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignResponse:
    return await lead_service.patch_campaign(db, ctx.site_id, campaign_id, body)


@router.delete("/lead-management/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await lead_service.delete_campaign(db, ctx.site_id, campaign_id))


@router.post("/lead-management/runs", status_code=201)
async def create_run(
    body: RunCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await lead_service.create_run(db, ctx.user_id, ctx.site_id, body.campaign_id)


@router.get("/lead-management/runs")
async def list_runs(
    campaign_id: str | None = Query(None, alias="campaignId"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[RunResponse]:
    return await lead_service.list_runs(db, ctx.site_id, campaign_id, paging)


@router.get("/lead-management/runs/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await lead_service.get_run(db, ctx.site_id, run_id)


@router.patch("/lead-management/runs/{run_id}")
async def patch_run(
    run_id: str,
    body: RunUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await lead_service.patch_run(db, ctx.site_id, run_id, body)


@router.post("/lead-management/leads/bulk")
async def bulk_add_leads(
    body: LeadsBulkRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BulkLeadsResponse:
    return await lead_service.bulk_add_leads(db, ctx.user_id, ctx.site_id, body)


@router.post("/lead-management/leads", status_code=201)
async def create_lead(
    body: LeadCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
):
    try:
        return await lead_service.create_lead(db, ctx.user_id, ctx.site_id, body)
    except LeadExistsError as exc:
        return JSONResponse(
            {
                "error": {
                    "message": "This lead is already in your pipeline.",
                    "leadId": exc.lead_id,
                }
            },
            status_code=409,
        )


@router.get("/lead-management/leads")
async def list_leads(
    stage: str | None = Query(None),
    campaign_id: str | None = Query(None, alias="campaignId"),
    source: str | None = Query(None),
    q: str | None = Query(None),
    has_email: bool | None = Query(None, alias="hasEmail"),
    min_fit: float | None = Query(None, alias="minFit"),
    sort: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[LeadResponse]:
    filters = LeadFilters(
        stage=stage,
        campaign_id=campaign_id,
        source=source,
        q=q,
        has_email=has_email,
        min_fit=min_fit,
        sort=sort,
    )
    return await lead_service.list_leads(db, ctx.site_id, filters, paging)


@router.get("/lead-management/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LeadResponse:
    return await lead_service.get_lead(db, ctx.site_id, lead_id)


@router.patch("/lead-management/leads/{lead_id}")
async def patch_lead(
    lead_id: str,
    body: LeadPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LeadResponse:
    return await lead_service.patch_lead(db, ctx.site_id, lead_id, body)


@router.delete("/lead-management/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await lead_service.delete_lead(db, ctx.site_id, lead_id))


@router.get("/lead-management/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SummaryResponse:
    return await lead_service.summary(db, ctx.site_id)
