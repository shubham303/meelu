from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.profile import repository as repo
from src.profile.schemas import ProfileCreateRequest, ProfileRecord, ProfileUpdateRequest


async def get_profile(db: AsyncSession, user_id: str) -> ProfileRecord | None:
    return await repo.get_profile(db, user_id)


async def upsert_profile(
    db: AsyncSession, user_id: str, body: ProfileCreateRequest
) -> ProfileRecord:
    values = body.changes()
    if await repo.get_profile(db, user_id) is None:
        if not values.get("full_name"):
            raise HTTPException(400, "fullName is required.")
        return await repo.create_profile(db, user_id, values)
    updated = await repo.update_profile(db, user_id, values)
    if updated is None:
        raise HTTPException(404, "Not found")
    return updated


async def patch_profile(
    db: AsyncSession, user_id: str, body: ProfileUpdateRequest
) -> ProfileRecord:
    updated = await repo.update_profile(db, user_id, body.changes())
    if updated is None:
        raise HTTPException(404, "No profile yet — PUT /api/v1/profile with fullName first.")
    return updated


async def delete_profile(db: AsyncSession, user_id: str) -> ProfileRecord:
    record = await repo.get_profile(db, user_id)
    if record is None:
        raise HTTPException(404, "Not found")
    await repo.delete_profile(db, user_id)
    return record
