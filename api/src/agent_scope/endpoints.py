from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent_scope.schemas import AgentScopeResponse
from src.agent_scope.service import agent_scope_service
from src.auth import current_user_id
from src.core.database import get_db

router = APIRouter()


@router.get("/agent/scope")
async def agent_scope(
    action: str | None = Query(None),
    name: str | None = Query(None),
    desks: str | None = Query(None),
    site_id: str | None = Header(None, alias="x-meelu-site"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AgentScopeResponse:
    resolved_action = action if action is not None else (name or "")
    return await agent_scope_service.scope(db, user_id, resolved_action, site_id, desks or "")
