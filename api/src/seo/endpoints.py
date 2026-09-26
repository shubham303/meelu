from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.clusters.endpoints import router as clusters_router
from src.seo.collect.endpoints import router as collect_router
from src.seo.competitors.endpoints import router as competitors_router
from src.seo.export.endpoints import router as export_router
from src.seo.gap.endpoints import router as gap_router
from src.seo.generators.endpoints import router as generators_router
from src.seo.jobs.endpoints import router as jobs_router
from src.seo.keywords.endpoints import router as keywords_router
from src.seo.page_facts.endpoints import router as page_facts_router
from src.seo.page_suggestions.endpoints import router as page_suggestions_router
from src.seo.pipeline.endpoints import router as pipeline_router
from src.seo.precompute.endpoints import router as precompute_router
from src.seo.schemas import OverviewResponse
from src.seo.service import seo_service
from src.seo.state.endpoints import router as state_router

router = APIRouter(prefix="/seo")


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> OverviewResponse:
    return await seo_service.overview(db, ctx.user_id, ctx.site_id)


for sub in (
    state_router,
    precompute_router,
    jobs_router,
    page_facts_router,
    keywords_router,
    clusters_router,
    competitors_router,
    pipeline_router,
    generators_router,
    gap_router,
    collect_router,
    page_suggestions_router,
    export_router,
):
    router.include_router(sub)
