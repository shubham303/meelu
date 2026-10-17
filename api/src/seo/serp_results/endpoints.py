from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.providers.registry import Caller
from src.seo.serp_results.schemas import SerpResults, SerpResultsRequest
from src.seo.serp_results.service import serp_results_service
from src.sites.service import site_service

router = APIRouter()


@router.post("/site/seo/serp-results")
async def serp_results(
    body: SerpResultsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SerpResults:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await serp_results_service.results(
        db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), site, body
    )
