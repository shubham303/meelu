from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models.social_accounts import SocialAccount
from src.content.schemas.publishing import SocialAccountRecord
from src.core.ids import uid


async def get_social_account(
    db: AsyncSession, user_id: str, site_id: str
) -> SocialAccountRecord | None:
    row = (
        await db.execute(
            select(SocialAccount)
            .where(SocialAccount.user_id == user_id, SocialAccount.site_id == site_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    return None if row is None else SocialAccountRecord.model_validate(row)


async def upsert_social_account(
    db: AsyncSession, user_id: str, site_id: str, provider: str, external_account_id: str
) -> SocialAccountRecord:
    now = datetime.now(UTC)
    row = (
        await db.execute(
            select(SocialAccount)
            .where(SocialAccount.user_id == user_id, SocialAccount.site_id == site_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        row = SocialAccount(
            id=uid("soc"),
            user_id=user_id,
            site_id=site_id,
            provider=provider,
            external_account_id=external_account_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.provider = provider
        row.external_account_id = external_account_id
        row.updated_at = now
    await db.flush()
    return SocialAccountRecord.model_validate(row)


async def delete_social_account(db: AsyncSession, user_id: str, site_id: str) -> bool:
    result = await db.execute(
        delete(SocialAccount)
        .where(SocialAccount.user_id == user_id, SocialAccount.site_id == site_id)
        .returning(SocialAccount.id)
    )
    return result.scalars().first() is not None
