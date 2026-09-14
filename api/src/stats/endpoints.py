from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import OptionalSiteContext, optional_site
from src.core.database import get_db
from src.stats import service
from src.stats.schemas import StatsResponse

router = APIRouter()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    ctx: OptionalSiteContext = Depends(optional_site),
) -> StatsResponse:
    if ctx.site_id is None:
        return StatsResponse.model_validate(service.empty_stats())
    return StatsResponse.model_validate(await service.get_stats(db, ctx.user_id, ctx.site_id))
