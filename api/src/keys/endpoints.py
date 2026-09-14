from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.keys import service
from src.keys.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyDeleteResponse,
    ApiKeyListItemResponse,
)

router = APIRouter()


@router.get("/keys")
async def list_keys(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("keys", "read")),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[ApiKeyListItemResponse]:
    page = await service.list_keys(db, user_id, paging)
    return PaginatedApiResponse[ApiKeyListItemResponse](
        data=[ApiKeyListItemResponse.model_validate(k) for k in page.data],
        pagination=page.pagination,
    )


@router.post("/keys", status_code=201)
async def create_key(
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("keys", "write")),
) -> ApiKeyCreatedResponse:
    result = await service.create_key(db, user_id, body)
    return ApiKeyCreatedResponse.model_validate({**dict(result.key), "key": result.raw})


@router.delete("/keys/{key_id}")
async def revoke_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("keys", "write")),
) -> ApiKeyDeleteResponse:
    record = await service.revoke_key(db, user_id, key_id)
    return ApiKeyDeleteResponse(id=record.id)
