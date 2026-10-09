from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.providers.registry import Caller
from src.seo.keyword_tracking.schemas import RankingsTracked, TrackedOverview, TrackKeywordsRequest
from src.seo.keyword_tracking.service import keyword_tracking_service
from src.seo.market import markets
from src.sites.service import site_service

router = APIRouter()


@router.get("/site/seo/tracked")
async def tracked_overview(
    location_code: int | None = Query(None, alias="locationCode"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TrackedOverview:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await keyword_tracking_service.overview(db, site, location_code)


@router.post("/site/seo/tracked/rankings")
async def track_rankings(
    body: TrackKeywordsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankingsTracked:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await keyword_tracking_service.track_rankings(
        db,
        Caller(user_id=ctx.user_id, site_id=ctx.site_id),
        ctx.user_id,
        ctx.site_id,
        site.domain,
        body,
        markets(site.markets, site.language),
    )
