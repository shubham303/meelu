from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.profile.models.profile import Profile
from src.profile.schemas import ProfileRecord

PROTECTED = frozenset({"id", "user_id", "created_at", "updated_at"})


def _writable(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if k not in PROTECTED}


async def _row(db: AsyncSession, user_id: str) -> Profile | None:
    return (
        await db.execute(select(Profile).where(Profile.user_id == user_id).limit(1))
    ).scalar_one_or_none()


async def get_profile(db: AsyncSession, user_id: str) -> ProfileRecord | None:
    row = await _row(db, user_id)
    return None if row is None else ProfileRecord.model_validate(row)


async def create_profile(db: AsyncSession, user_id: str, values: dict[str, Any]) -> ProfileRecord:
    now = datetime.now(UTC)
    row = Profile(
        id=uid("prof"), user_id=user_id, created_at=now, updated_at=now, **_writable(values)
    )
    db.add(row)
    await db.flush()
    return ProfileRecord.model_validate(row)


async def update_profile(
    db: AsyncSession, user_id: str, values: dict[str, Any]
) -> ProfileRecord | None:
    row = await _row(db, user_id)
    if row is None:
        return None
    for key, value in _writable(values).items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    await db.flush()
    return ProfileRecord.model_validate(row)


async def delete_profile(db: AsyncSession, user_id: str) -> None:
    row = await _row(db, user_id)
    if row is None:
        return
    await db.delete(row)
    await db.flush()
