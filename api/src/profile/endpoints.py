from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require
from src.core.database import get_db
from src.profile.service import profile_service
from src.profile.schemas import (
    ProfileCreateRequest,
    ProfileDeleteResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)

router = APIRouter()


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "read")),
) -> ProfileResponse | None:
    record = await profile_service.get(db, user_id)
    return None if record is None else ProfileResponse.model_validate(record)


@router.put("/profile")
async def upsert_profile(
    body: ProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "write")),
) -> ProfileResponse:
    return ProfileResponse.model_validate(await profile_service.upsert(db, user_id, body))


@router.patch("/profile")
async def patch_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "write")),
) -> ProfileResponse:
    return ProfileResponse.model_validate(await profile_service.update(db, user_id, body))


@router.delete("/profile")
async def delete_profile(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "write")),
) -> ProfileDeleteResponse:
    record = await profile_service.delete(db, user_id)
    return ProfileDeleteResponse(id=record.id)
