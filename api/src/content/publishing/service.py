from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.channels import service as channels_service
from src.content.publishing import repository as repo
from src.content.schemas.publishing import SocialAccountRecord, SocialAccountUpsertRequest


async def get_account(db: AsyncSession, user_id: str, site_id: str) -> SocialAccountRecord:
    account = await repo.get_social_account(db, user_id, site_id)
    if account is None:
        raise HTTPException(404, "This website has no publishing account yet.")
    return account


async def upsert_account(
    db: AsyncSession, user_id: str, site_id: str, body: SocialAccountUpsertRequest
) -> SocialAccountRecord:
    return await repo.upsert_social_account(
        db, user_id, site_id, body.provider, body.external_account_id
    )


async def delete_account(db: AsyncSession, user_id: str, site_id: str) -> None:
    if not await repo.delete_social_account(db, user_id, site_id):
        raise HTTPException(404, "This website has no publishing account yet.")


async def sync_channels(db: AsyncSession, user_id: str, site_id: str, platforms: list[str]) -> None:
    await channels_service.sync_enabled(db, user_id, site_id, set(platforms))
