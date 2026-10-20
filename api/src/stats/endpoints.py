from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import OptionalSiteContext, optional_site
from src.core.database import get_db
from src.stats.schemas import StatsResponse
from src.stats.service import stats_service

router = APIRouter()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    ctx: OptionalSiteContext = Depends(optional_site),
) -> StatsResponse:
    if ctx.site_id is None:
        return StatsResponse.model_validate(stats_service.empty())
    return StatsResponse.model_validate(await stats_service.get(db, ctx.user_id, ctx.site_id))
