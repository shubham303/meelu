from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.providers.registry import Caller
from src.seo.serp_history.schemas import SerpHistory, SerpHistoryRequest
from src.seo.serp_history.service import serp_history_service
from src.sites.service import site_service

router = APIRouter()


@router.post("/site/seo/serp-history")
async def keyword_serp_history(
    body: SerpHistoryRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SerpHistory:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await serp_history_service.history(
        db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), site, body
    )
