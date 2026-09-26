from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.state.schemas import SiteStateRecord, SiteStateUpdateRequest
from src.seo.state.service import seo_state_service

router = APIRouter()


@router.get("/state")
async def get_state(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> SiteStateRecord:
    return await seo_state_service.get(db, ctx.user_id, ctx.site_id)


@router.patch("/state")
async def patch_state(
    body: SiteStateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteStateRecord:
    return await seo_state_service.patch(db, ctx.user_id, ctx.site_id, body)
