from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.content.publishing import service
from src.content.schemas.publishing import (
    SocialAccountDeleteResponse,
    SocialAccountResponse,
    SocialAccountUpsertRequest,
    SocialChannelsSyncRequest,
    SocialChannelsSyncResponse,
)
from src.core.database import get_db

router = APIRouter()


@router.get("/social/account")
async def get_account(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SocialAccountResponse:
    account = await service.get_account(db, ctx.user_id, ctx.site_id)
    return SocialAccountResponse.model_validate(account)


@router.put("/social/account")
async def upsert_account(
    body: SocialAccountUpsertRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SocialAccountResponse:
    account = await service.upsert_account(db, ctx.user_id, ctx.site_id, body)
    return SocialAccountResponse.model_validate(account)


@router.delete("/social/account")
async def delete_account(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SocialAccountDeleteResponse:
    await service.delete_account(db, ctx.user_id, ctx.site_id)
    return SocialAccountDeleteResponse()


@router.post("/social/channels/sync")
async def sync_channels(
    body: SocialChannelsSyncRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SocialChannelsSyncResponse:
    await service.sync_channels(db, ctx.user_id, ctx.site_id, body.platforms)
    return SocialChannelsSyncResponse()
