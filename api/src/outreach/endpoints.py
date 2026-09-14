from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.outreach import service
from src.outreach.schemas import (
    CampaignCreateRequest,
    CampaignDeleteResponse,
    CampaignListItemResponse,
    CampaignResponse,
    CampaignUpdateRequest,
    ConversationCreateRequest,
    ConversationDeleteResponse,
    ConversationListItemResponse,
    ConversationResponse,
    ConversationSyncRequest,
    ConversationSyncResponse,
    ConversationUpdateRequest,
    KnownProspectsResponse,
    OutreachProjectCreateRequest,
    OutreachProjectDeleteResponse,
    OutreachProjectListItemResponse,
    OutreachProjectResponse,
    OutreachProjectUpdateRequest,
    ProspectBulkCreateRequest,
    ProspectBulkCreateResponse,
    ProspectCreateRequest,
    ProspectDeleteResponse,
    ProspectListItemResponse,
    ProspectResponse,
    ProspectUpdateRequest,
)

router = APIRouter()


@router.get("/outreach/projects")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[OutreachProjectListItemResponse]:
    page = await service.list_projects(db, ctx.user_id, ctx.site_id, paging)
    return PaginatedApiResponse[OutreachProjectListItemResponse](
        data=[OutreachProjectListItemResponse.model_validate(p) for p in page.data],
        pagination=page.pagination,
    )


@router.post("/outreach/projects", status_code=201)
async def create_project(
    body: OutreachProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> OutreachProjectResponse:
    record = await service.create_project(db, ctx.user_id, ctx.site_id, body)
    return OutreachProjectResponse.model_validate(record)


@router.get("/outreach/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> OutreachProjectResponse:
    record = await service.get_project(db, ctx.user_id, ctx.site_id, project_id)
    return OutreachProjectResponse.model_validate(record)


@router.put("/outreach/projects/{project_id}")
async def update_project(
    project_id: str,
    body: OutreachProjectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> OutreachProjectResponse:
    record = await service.update_project(db, ctx.user_id, ctx.site_id, project_id, body)
    return OutreachProjectResponse.model_validate(record)


@router.delete("/outreach/projects/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> OutreachProjectDeleteResponse:
    record = await service.delete_project(db, ctx.user_id, ctx.site_id, project_id)
    return OutreachProjectDeleteResponse(id=record.id)


@router.get("/outreach/projects/{project_id}/known-prospects")
async def known_prospects(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> KnownProspectsResponse:
    return await service.list_known_prospects(db, ctx.user_id, ctx.site_id, project_id)


@router.get("/outreach/campaigns")
async def list_campaigns(
    project_id: str | None = Query(None, alias="projectId"),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[CampaignListItemResponse]:
    page = await service.list_campaigns(db, ctx.user_id, ctx.site_id, paging, project_id, status)
    return PaginatedApiResponse[CampaignListItemResponse](
        data=[CampaignListItemResponse.model_validate(c) for c in page.data],
        pagination=page.pagination,
    )


@router.post("/outreach/campaigns", status_code=201)
async def create_campaign(
    body: CampaignCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignResponse:
    record = await service.create_campaign(db, ctx.user_id, ctx.site_id, body)
    return CampaignResponse.model_validate(record)


@router.get("/outreach/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignResponse:
    record = await service.get_campaign(db, ctx.user_id, ctx.site_id, campaign_id)
    return CampaignResponse.model_validate(record)


@router.put("/outreach/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignResponse:
    record = await service.update_campaign(db, ctx.user_id, ctx.site_id, campaign_id, body)
    return CampaignResponse.model_validate(record)


@router.delete("/outreach/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CampaignDeleteResponse:
    record = await service.delete_campaign(db, ctx.user_id, ctx.site_id, campaign_id)
    return CampaignDeleteResponse(id=record.id)


@router.get("/outreach/prospects")
async def list_prospects(
    campaign_id: str | None = Query(None, alias="campaignId"),
    project_id: str | None = Query(None, alias="projectId"),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[ProspectListItemResponse]:
    page = await service.list_prospects(
        db, ctx.user_id, ctx.site_id, paging, campaign_id, project_id, status
    )
    return PaginatedApiResponse[ProspectListItemResponse](
        data=[ProspectListItemResponse.model_validate(p) for p in page.data],
        pagination=page.pagination,
    )


@router.post("/outreach/prospects", status_code=201)
async def create_prospects(
    body: ProspectBulkCreateRequest | ProspectCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ProspectBulkCreateResponse | ProspectResponse:
    if isinstance(body, ProspectBulkCreateRequest):
        result = await service.create_prospects(db, ctx.user_id, ctx.site_id, body.prospects)
        return ProspectBulkCreateResponse(
            created=[ProspectResponse.model_validate(p) for p in result.created],
            skipped=result.skipped,
        )
    record = await service.create_prospect(db, ctx.user_id, ctx.site_id, body)
    return ProspectResponse.model_validate(record)


@router.get("/outreach/prospects/{prospect_id}")
async def get_prospect(
    prospect_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ProspectResponse:
    record = await service.get_prospect(db, ctx.user_id, ctx.site_id, prospect_id)
    return ProspectResponse.model_validate(record)


@router.put("/outreach/prospects/{prospect_id}")
async def update_prospect(
    prospect_id: str,
    body: ProspectUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ProspectResponse:
    record = await service.update_prospect(db, ctx.user_id, ctx.site_id, prospect_id, body)
    return ProspectResponse.model_validate(record)


@router.delete("/outreach/prospects/{prospect_id}")
async def delete_prospect(
    prospect_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ProspectDeleteResponse:
    record = await service.delete_prospect(db, ctx.user_id, ctx.site_id, prospect_id)
    return ProspectDeleteResponse(id=record.id)


@router.get("/outreach/conversations")
async def list_conversation(
    prospect_id: str | None = Query(None, alias="prospectId"),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[ConversationListItemResponse]:
    page = await service.list_conversation(
        db, ctx.user_id, ctx.site_id, paging, prospect_id, status
    )
    return PaginatedApiResponse[ConversationListItemResponse](
        data=[ConversationListItemResponse.model_validate(m) for m in page.data],
        pagination=page.pagination,
    )


@router.post("/outreach/conversations", status_code=201)
async def create_conversation(
    body: ConversationSyncRequest | ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConversationSyncResponse | ConversationResponse:
    if isinstance(body, ConversationSyncRequest):
        result = await service.sync_conversation_messages(
            db, ctx.user_id, ctx.site_id, body.messages
        )
        return ConversationSyncResponse(
            added=[ConversationResponse.model_validate(m) for m in result.added],
            skipped=result.skipped,
        )
    record = await service.create_conversation_message(db, ctx.user_id, ctx.site_id, body)
    return ConversationResponse.model_validate(record)


@router.get("/outreach/conversations/{message_id}")
async def get_conversation(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConversationResponse:
    record = await service.get_conversation_message(db, ctx.user_id, ctx.site_id, message_id)
    return ConversationResponse.model_validate(record)


@router.put("/outreach/conversations/{message_id}")
async def update_conversation(
    message_id: str,
    body: ConversationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConversationResponse:
    record = await service.update_conversation_message(
        db, ctx.user_id, ctx.site_id, message_id, body
    )
    return ConversationResponse.model_validate(record)


@router.delete("/outreach/conversations/{message_id}")
async def delete_conversation(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConversationDeleteResponse:
    record = await service.delete_conversation_message(db, ctx.user_id, ctx.site_id, message_id)
    return ConversationDeleteResponse(id=record.id)
