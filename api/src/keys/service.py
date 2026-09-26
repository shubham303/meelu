from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.keys.repository import api_keys
from src.keys.schemas import ApiKeyCreateRequest, ApiKeyCreateResult, ApiKeyRecord


class ApiKeyService:
    async def list(
        self, db: AsyncSession, user_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[ApiKeyRecord]:
        return await api_keys.list(db, user_id, paging)

    async def create(
        self, db: AsyncSession, user_id: str, body: ApiKeyCreateRequest
    ) -> ApiKeyCreateResult:
        return await api_keys.create(db, user_id, body.name)

    async def revoke(self, db: AsyncSession, user_id: str, key_id: str) -> ApiKeyRecord:
        record = await api_keys.get(db, user_id, key_id)
        if record is None:
            raise HTTPException(404, "Not found")
        if await api_keys.count(db, user_id) <= 1:
            raise HTTPException(400, "Cannot revoke the last remaining API key.")
        await api_keys.delete(db, user_id, key_id)
        return record


api_key_service = ApiKeyService()
