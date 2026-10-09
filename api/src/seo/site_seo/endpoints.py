from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.site_seo.constants import SeoList
from src.seo.site_seo.schemas import SeoListChange, SeoListItemsRequest, SiteSeoRecord
from src.seo.site_seo.service import site_seo_service

router = APIRouter()


@router.get("/site/seo")
async def get_site_seo(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteSeoRecord:
    return await site_seo_service.get(db, ctx.site_id)


@router.post("/site/seo/{name}/add")
async def add_site_seo_items(
    name: SeoList,
    body: SeoListItemsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SeoListChange:
    return await site_seo_service.add_items(db, ctx.user_id, ctx.site_id, name, body.items)


@router.post("/site/seo/{name}/remove")
async def remove_site_seo_items(
    name: SeoList,
    body: SeoListItemsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SeoListChange:
    return await site_seo_service.remove_items(db, ctx.user_id, ctx.site_id, name, body.items)
