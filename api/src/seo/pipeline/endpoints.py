from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.pipeline.schemas import (
    RankRequest,
    RankResult,
    ReconcileResult,
    ReviewBatch,
    ReviewInputsRequest,
    ReviewResult,
    ScreenRequest,
    ScreenResult,
    VerdictRequest,
)
from src.seo.pipeline.service import seo_pipeline_service

router = APIRouter()


@router.post("/reconcile")
async def reconcile(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> ReconcileResult:
    return await seo_pipeline_service.reconcile(db, ctx.user_id, ctx.site_id)


@router.post("/page-suggestions/screen")
async def screen_suggestions(
    body: ScreenRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ScreenResult:
    return await seo_pipeline_service.screen(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/review-inputs")
async def page_suggestion_review_inputs(
    body: ReviewInputsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewBatch:
    return await seo_pipeline_service.review_inputs(db, ctx.site_id, body)


@router.post("/page-suggestions/verdicts")
async def page_suggestion_verdicts(
    body: VerdictRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewResult:
    return await seo_pipeline_service.apply_verdicts(db, ctx.site_id, body)


@router.post("/page-suggestions/rank")
async def rank_suggestions(
    body: RankRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankResult:
    return await seo_pipeline_service.rank(db, ctx.site_id, body)
