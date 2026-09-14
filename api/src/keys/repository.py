import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.keys.models.api_key import ApiKey
from src.keys.schemas import ApiKeyCreateResult, ApiKeyOwner, ApiKeyRecord


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def preview_of(raw: str) -> str:
    return f"{raw[:9]}…{raw[-4:]}"


async def list_keys(
    db: AsyncSession, user_id: str, paging: PaginationParams
) -> PaginatedApiResponse[ApiKeyRecord]:
    query = select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.seq.desc())
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, ApiKeyRecord
    )


async def get_key(db: AsyncSession, user_id: str, key_id: str) -> ApiKeyRecord | None:
    row = (
        await db.execute(select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.id == key_id))
    ).scalar_one_or_none()
    return None if row is None else ApiKeyRecord.model_validate(row)


async def count_keys(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user_id)
    )
    return result.scalar_one()


async def create_key(db: AsyncSession, user_id: str, name: str) -> ApiKeyCreateResult:
    now = datetime.now(UTC)
    raw = f"emcp_{secrets.token_hex(32)}"
    row = ApiKey(
        id=uid("key"),
        user_id=user_id,
        name=name,
        key_hash=hash_key(raw),
        preview=preview_of(raw),
        last_used_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return ApiKeyCreateResult(key=ApiKeyRecord.model_validate(row), raw=raw)


async def delete_key(db: AsyncSession, user_id: str, key_id: str) -> None:
    row = (
        await db.execute(select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.id == key_id))
    ).scalar_one_or_none()
    if row is None:
        return
    await db.delete(row)
    await db.flush()


async def find_user_by_api_key(db: AsyncSession, raw: str) -> ApiKeyOwner | None:
    result = await db.execute(
        update(ApiKey)
        .where(ApiKey.key_hash == hash_key(raw))
        .values(last_used_at=datetime.now(UTC))
        .returning(ApiKey.user_id)
    )
    row = result.first()
    return None if row is None else ApiKeyOwner(user_id=row[0])
