from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require
from src.core.database import get_db
from src.profile import service
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
    record = await service.get_profile(db, user_id)
    return None if record is None else ProfileResponse.model_validate(record)


@router.put("/profile")
async def upsert_profile(
    body: ProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "write")),
) -> ProfileResponse:
    return ProfileResponse.model_validate(await service.upsert_profile(db, user_id, body))


@router.patch("/profile")
async def patch_profile(
    body: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "write")),
) -> ProfileResponse:
    return ProfileResponse.model_validate(await service.patch_profile(db, user_id, body))


@router.delete("/profile")
async def delete_profile(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("profile", "write")),
) -> ProfileDeleteResponse:
    record = await service.delete_profile(db, user_id)
    return ProfileDeleteResponse(id=record.id)
