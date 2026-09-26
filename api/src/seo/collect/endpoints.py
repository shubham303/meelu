from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.collect.schemas import (
    CollectCompetitorKeywordsRequest,
    CollectCompetitorsRequest,
    CollectKeywordsRequest,
    CollectResult,
    CollectSerpsRequest,
)
from src.seo.collect.service import seo_collect_service

router = APIRouter()


@router.post("/collect/keywords")
async def collect_keywords(
    body: CollectKeywordsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await seo_collect_service.collect_keywords(db, ctx.user_id, ctx.site_id, body)


@router.post("/collect/competitors")
async def collect_competitors(
    body: CollectCompetitorsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await seo_collect_service.collect_competitors(db, ctx.user_id, ctx.site_id, body)


@router.post("/collect/competitor-keywords")
async def collect_competitor_keywords(
    body: CollectCompetitorKeywordsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await seo_collect_service.collect_competitor_keywords(db, ctx.user_id, ctx.site_id, body)


@router.post("/collect/serps")
async def collect_serps(
    body: CollectSerpsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await seo_collect_service.collect_serps(db, ctx.user_id, ctx.site_id, body)
