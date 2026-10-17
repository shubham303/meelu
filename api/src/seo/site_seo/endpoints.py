from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.providers.registry import Caller
from src.seo.site_seo.schemas import (
    BacklinkOpportunity,
    BacklinksFetched,
    Competitor,
    CompetitorsChange,
    DomainsRequest,
    OpportunitiesDismissed,
)
from src.seo.site_seo.service import site_seo_service
from src.sites.service import site_service

router = APIRouter()


@router.get("/site/seo/competitors")
async def list_competitors(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[Competitor]:
    return await site_seo_service.list_competitors(db, ctx.site_id)


@router.post("/site/seo/competitors")
async def add_competitors(
    body: DomainsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CompetitorsChange:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await site_seo_service.add_competitors(
        db,
        Caller(user_id=ctx.user_id, site_id=ctx.site_id),
        ctx.user_id,
        ctx.site_id,
        site.domain,
        body.domains,
    )


@router.delete("/site/seo/competitors/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> Response:
    await site_seo_service.delete_competitor(db, ctx.site_id, competitor_id)
    return Response(status_code=204)


@router.post("/site/seo/backlinks/fetch")
async def fetch_backlinks(
    body: DomainsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BacklinksFetched:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await site_seo_service.fetch_backlinks(
        db,
        Caller(user_id=ctx.user_id, site_id=ctx.site_id),
        ctx.user_id,
        ctx.site_id,
        site.domain,
        body.domains,
    )


@router.get("/site/seo/backlink-opportunities")
async def list_backlink_opportunities(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[BacklinkOpportunity]:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await site_seo_service.opportunities(db, ctx.site_id, site.domain, paging)


@router.post("/site/seo/backlink-opportunities/dismiss")
async def dismiss_backlink_opportunities(
    body: DomainsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> OpportunitiesDismissed:
    return await site_seo_service.dismiss_opportunities(db, ctx.site_id, body.domains)
