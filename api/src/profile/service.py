from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.profile.repository import profiles
from src.profile.schemas import ProfileCreateRequest, ProfileRecord, ProfileUpdateRequest


class ProfileService:
    async def get(self, db: AsyncSession, user_id: str) -> ProfileRecord | None:
        return await profiles.get(db, user_id)

    async def upsert(
        self, db: AsyncSession, user_id: str, body: ProfileCreateRequest
    ) -> ProfileRecord:
        values = body.changes()
        if await profiles.get(db, user_id) is None:
            if not values.get("full_name"):
                raise HTTPException(400, "fullName is required.")
            return await profiles.create(db, user_id, values)
        updated = await profiles.update(db, user_id, values)
        if updated is None:
            raise HTTPException(404, "Not found")
        return updated

    async def update(
        self, db: AsyncSession, user_id: str, body: ProfileUpdateRequest
    ) -> ProfileRecord:
        updated = await profiles.update(db, user_id, body.changes())
        if updated is None:
            raise HTTPException(404, "No profile yet — PUT /api/v1/profile with fullName first.")
        return updated

    async def delete(self, db: AsyncSession, user_id: str) -> ProfileRecord:
        record = await profiles.get(db, user_id)
        if record is None:
            raise HTTPException(404, "Not found")
        await profiles.delete(db, user_id)
        return record


profile_service = ProfileService()
