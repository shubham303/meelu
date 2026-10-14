from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.user_prompts.schemas import (
    UserPromptCreateRequest,
    UserPromptDeleteResponse,
    UserPromptListFilters,
    UserPromptListItemResponse,
    UserPromptResponse,
    UserPromptSurface,
    UserPromptUpdateRequest,
)
from src.user_prompts.service import user_prompt_service

router = APIRouter()


@router.get("/user-prompts")
async def list_user_prompts(
    surface: UserPromptSurface | None = Query(None),
    contains: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[UserPromptListItemResponse]:
    filters = UserPromptListFilters(surface=surface, contains=contains)
    page = await user_prompt_service.list_prompts(db, ctx.site_id, filters, paging)
    return PaginatedApiResponse[UserPromptListItemResponse](
        data=[UserPromptListItemResponse.model_validate(p) for p in page.data],
        pagination=page.pagination,
    )


@router.post("/user-prompts", status_code=201)
async def create_user_prompt(
    body: UserPromptCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> UserPromptResponse:
    record = await user_prompt_service.create_prompt(db, ctx.user_id, ctx.site_id, body)
    return UserPromptResponse.model_validate(record)


@router.get("/user-prompts/{prompt_id}")
async def get_user_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> UserPromptResponse:
    record = await user_prompt_service.get_prompt(db, ctx.site_id, prompt_id)
    return UserPromptResponse.model_validate(record)


@router.patch("/user-prompts/{prompt_id}")
async def update_user_prompt(
    prompt_id: str,
    body: UserPromptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> UserPromptResponse:
    record = await user_prompt_service.update_prompt(db, ctx.site_id, prompt_id, body)
    return UserPromptResponse.model_validate(record)


@router.delete("/user-prompts/{prompt_id}")
async def delete_user_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> UserPromptDeleteResponse:
    record = await user_prompt_service.delete_prompt(db, ctx.site_id, prompt_id)
    return UserPromptDeleteResponse(id=record.id)
