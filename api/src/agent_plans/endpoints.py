from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent_plans.service import agent_plan_service
from src.agent_plans.schemas import (
    AgentPlanCreateRequest,
    AgentPlanDeleteResponse,
    AgentPlanListItemResponse,
    AgentPlanResponse,
    AgentPlanUpdateRequest,
)
from src.auth import current_user_id
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params

router = APIRouter()


@router.get("/agent-plans")
async def list_plans(
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[AgentPlanListItemResponse]:
    page = await agent_plan_service.list_plans(db, user_id, paging, search=q)
    return PaginatedApiResponse[AgentPlanListItemResponse](
        data=[AgentPlanListItemResponse.model_validate(p) for p in page.data],
        pagination=page.pagination,
    )


@router.post("/agent-plans", status_code=201)
async def create_plan(
    body: AgentPlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AgentPlanResponse:
    record = await agent_plan_service.create_plan(db, user_id, body)
    return AgentPlanResponse.model_validate(record)


@router.get("/agent-plans/by-slug/{slug}")
async def get_plan_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AgentPlanResponse:
    record = await agent_plan_service.get_plan_by_slug(db, user_id, slug)
    return AgentPlanResponse.model_validate(record)


@router.get("/agent-plans/{plan_id}")
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AgentPlanResponse:
    record = await agent_plan_service.get_plan(db, user_id, plan_id)
    return AgentPlanResponse.model_validate(record)


@router.patch("/agent-plans/{plan_id}")
async def patch_plan(
    plan_id: str,
    body: AgentPlanUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AgentPlanResponse:
    record = await agent_plan_service.update_plan(db, user_id, plan_id, body)
    return AgentPlanResponse.model_validate(record)


@router.delete("/agent-plans/{plan_id}")
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AgentPlanDeleteResponse:
    record = await agent_plan_service.delete_plan(db, user_id, plan_id)
    return AgentPlanDeleteResponse(id=record.id)
