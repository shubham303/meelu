from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent_scope.lib import SiteRef
from src.agent_scope.schemas import AgentScopeResponse
from src.agent_scope.service import resolve_scope, scope_response
from src.auth import current_user_id
from src.core.database import get_db
from src.sites import repository as sites_repository

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
    scope = resolve_scope(resolved_action)

    if not site_id and not scope.is_global:
        raise HTTPException(400, "This action needs a website — send x-meelu-site.")

    site = await sites_repository.get_site(db, user_id, site_id) if site_id else None
    if site_id and site is None:
        raise HTTPException(404, f"No website {site_id} in this workspace.")

    site_ref = SiteRef(id=site.id, name=site.name, domain=site.domain) if site else None
    return scope_response(resolved_action, scope, site_ref, desks or "")
