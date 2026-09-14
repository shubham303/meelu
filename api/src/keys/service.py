from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.keys import repository as repo
from src.keys.schemas import ApiKeyCreateRequest, ApiKeyCreateResult, ApiKeyRecord


async def list_keys(
    db: AsyncSession, user_id: str, paging: PaginationParams
) -> PaginatedApiResponse[ApiKeyRecord]:
    return await repo.list_keys(db, user_id, paging)


async def create_key(
    db: AsyncSession, user_id: str, body: ApiKeyCreateRequest
) -> ApiKeyCreateResult:
    return await repo.create_key(db, user_id, body.name)


async def revoke_key(db: AsyncSession, user_id: str, key_id: str) -> ApiKeyRecord:
    record = await repo.get_key(db, user_id, key_id)
    if record is None:
        raise HTTPException(404, "Not found")
    if await repo.count_keys(db, user_id) <= 1:
        raise HTTPException(400, "Cannot revoke the last remaining API key.")
    await repo.delete_key(db, user_id, key_id)
    return record
