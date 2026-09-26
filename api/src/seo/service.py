from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.clusters.repository import seo_keyword_clusters
from src.seo.competitors.repository import seo_competitors
from src.seo.jobs.repository import seo_jobs
from src.seo.jobs.schemas import SeoJobCreateRequest, SeoJobRecord
from src.seo.keywords.repository import seo_keywords
from src.seo.page_suggestions.repository import seo_page_suggestions
from src.seo.pipeline.schemas import ReconcileResult
from src.seo.pipeline.service import seo_pipeline_service
from src.seo.precompute.rollup import seo_rollup_service
from src.seo.schemas import OverviewResponse
from src.seo.state.service import seo_state_service
from src.settings import settings


class SeoService:
    async def start_job(
        self, db: AsyncSession, user_id: str, site_id: str, body: SeoJobCreateRequest
    ) -> tuple[SeoJobRecord, ReconcileResult]:
        await seo_state_service.get(db, user_id, site_id)
        await seo_jobs.fail_running(db, site_id)
        await seo_rollup_service.run(db, user_id, site_id)
        reconciled = await seo_pipeline_service.reconcile(db, user_id, site_id)
        job = await seo_jobs.create(
            db, user_id, site_id, body.prompt, settings.seo_job_vendor_ceiling_micros
        )
        return job, reconciled

    async def overview(self, db: AsyncSession, user_id: str, site_id: str) -> OverviewResponse:
        state = await seo_state_service.get(db, user_id, site_id)
        return OverviewResponse(
            keywords=await seo_keywords.count(db, site_id),
            keywords_with_facts=await seo_keywords.count(db, site_id, with_facts=True),
            clusters=await seo_keyword_clusters.count(db, site_id),
            competitors_confirmed=await seo_competitors.count(db, site_id, "confirmed"),
            suggestions=await seo_page_suggestions.summary(db, site_id),
            state=state,
        )


seo_service = SeoService()
