from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.jobs.service import seo_job_service
from src.seo.pipeline.ranking import seo_ranking_service
from src.seo.pipeline.reconcile import seo_reconcile_service
from src.seo.pipeline.review import seo_review_service
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
from src.seo.pipeline.screening import seo_screening_service
from src.seo.state.service import seo_state_service


class SeoPipelineService:
    async def reconcile(self, db: AsyncSession, user_id: str, site_id: str) -> ReconcileResult:
        state = await seo_state_service.get(db, user_id, site_id)
        return await seo_reconcile_service.reconcile(
            db, site_id, seo_state_service.precompute_pending(state)
        )

    async def screen(
        self, db: AsyncSession, user_id: str, site_id: str, body: ScreenRequest
    ) -> ScreenResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await seo_screening_service.screen(
            db, user_id, site_id, body.job_id, body.ids, body.question, body.limit
        )

    async def review_inputs(
        self, db: AsyncSession, site_id: str, body: ReviewInputsRequest
    ) -> ReviewBatch:
        await seo_job_service.get(db, site_id, body.job_id)
        return await seo_review_service.review_inputs(
            db, site_id, body.job_id, body.prompt, body.ids, body.limit
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, body: VerdictRequest
    ) -> ReviewResult:
        return await seo_review_service.apply_verdicts(db, site_id, body.verdicts)

    async def rank(self, db: AsyncSession, site_id: str, body: RankRequest) -> RankResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await seo_ranking_service.rank(
            db,
            site_id,
            body.job_id,
            {"add": body.budget_add, "edit": body.budget_edit, "delete": body.budget_delete},
        )


seo_pipeline_service = SeoPipelineService()
