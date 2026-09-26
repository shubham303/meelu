from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.collect import seo_collect_service
from src.seo.export import DATASETS, seo_export_service
from src.seo.gap import seo_gap_service
from src.seo.generators import seo_generator_service
from src.seo.precompute.embed import seo_embed_service
from src.seo.precompute.rollup import seo_rollup_service
from src.seo.ranking import seo_ranking_service
from src.seo.reconcile import seo_reconcile_service
from src.seo.review import seo_review_service
from src.seo.screening import seo_screening_service
from src.seo.suggestions import seo_suggestion_service
from src.seo.constants import OPEN_STATES
from src.seo.repositories import (
    seo_competitors,
    seo_jobs,
    seo_keyword_clusters,
    seo_keyword_content_pages,
    seo_keyword_gsc_pages,
    seo_keywords,
    seo_page_facts,
    seo_page_suggestions,
    seo_site_states,
)
from src.seo.schemas import (
    CannibalisationRequest,
    ClusterRecord,
    CollectCompetitorKeywordsRequest,
    CollectCompetitorsRequest,
    CollectKeywordsRequest,
    CollectResult,
    CollectSerpsRequest,
    CompetitorRecord,
    CompetitorUpdateRequest,
    CreateResult,
    GapPagesRequest,
    KeywordContentPageRecord,
    KeywordFilter,
    KeywordGscPageRecord,
    KeywordRecord,
    NewPageSuggestion,
    OverviewResponse,
    PageEditsRequest,
    PageFactsRecord,
    PageSuggestionFilter,
    PageSuggestionRecord,
    RankRequest,
    RankResult,
    ReconcileResult,
    ReviewBatch,
    ReviewInputsRequest,
    ReviewResult,
    RollupResult,
    SavePageSuggestionRequest,
    ScreenRequest,
    ScreenResult,
    SeoJobCreateRequest,
    SeoJobRecord,
    SeoJobUpdateRequest,
    SiteStateRecord,
    SiteStateUpdateRequest,
    TopicPagesRequest,
    TopicPagesResult,
    VerdictRequest,
)
from src.settings import settings

JOB_NOT_FOUND = "No such SEO job on this website."

SUGGESTION_NOT_FOUND = "No such page suggestion on this website."

COMPETITOR_NOT_FOUND = "No such competitor on this website."

KEYWORD_NOT_FOUND = "No such keyword on this website."


class SeoService:
    async def get_state(self, db: AsyncSession, user_id: str, site_id: str) -> SiteStateRecord:
        return await seo_site_states.ensure(db, user_id, site_id)

    async def patch_state(
        self, db: AsyncSession, user_id: str, site_id: str, body: SiteStateUpdateRequest
    ) -> SiteStateRecord:
        await seo_site_states.ensure(db, user_id, site_id)
        patch = body.model_dump(exclude_none=True)
        if not patch:
            return await seo_site_states.ensure(db, user_id, site_id)
        updated = await seo_site_states.patch(db, site_id, patch)
        if "brand_terms" in patch:
            await seo_keywords.mark_branded(db, site_id, patch["brand_terms"])
        return updated

    async def run_rollup(self, db: AsyncSession, user_id: str, site_id: str) -> RollupResult:
        await seo_site_states.ensure(db, user_id, site_id)
        result = await seo_rollup_service.run(db, user_id, site_id)
        await db.commit()
        return result

    async def request_precompute(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> SiteStateRecord:
        await seo_site_states.ensure(db, user_id, site_id)
        await seo_site_states.request_precompute(db, site_id)
        found = await seo_site_states.get(db, site_id)
        assert found is not None
        return found

    async def reconcile(self, db: AsyncSession, user_id: str, site_id: str) -> ReconcileResult:
        state = await seo_site_states.ensure(db, user_id, site_id)
        pending = state.embedded_at is None or (
            state.precompute_requested_at is not None
            and state.precompute_requested_at > state.embedded_at
        )
        return await seo_reconcile_service.reconcile(db, site_id, pending)

    async def save_suggestion(
        self, db: AsyncSession, user_id: str, site_id: str, body: SavePageSuggestionRequest
    ) -> CreateResult:
        await self.get_job(db, site_id, body.job_id)
        keyword_ids = list(body.keyword_ids)
        if body.terms:
            keyword_ids += await self.add_keywords(db, user_id, site_id, body.terms, "user")
        new = NewPageSuggestion(
            action=body.action,
            topic_key=body.topic_key,
            page_id=body.page_id,
            merge_into_page_id=body.merge_into_page_id,
            keyword_ids=keyword_ids,
            strategy="agent",
            suggestion=body.suggestion,
            evidence=body.evidence,
            state="ready",
        )
        return await seo_suggestion_service.create_many(db, user_id, site_id, body.job_id, [new])

    async def start_job(
        self, db: AsyncSession, user_id: str, site_id: str, body: SeoJobCreateRequest
    ) -> tuple[SeoJobRecord, ReconcileResult]:
        await seo_site_states.ensure(db, user_id, site_id)
        await seo_jobs.fail_running(db, site_id)
        await seo_rollup_service.run(db, user_id, site_id)
        reconciled = await self.reconcile(db, user_id, site_id)
        job = await seo_jobs.create(
            db, user_id, site_id, body.prompt, settings.seo_job_vendor_ceiling_micros
        )
        return job, reconciled

    async def get_job(self, db: AsyncSession, site_id: str, job_id: str) -> SeoJobRecord:
        found = await seo_jobs.get(db, site_id, job_id)
        if found is None:
            raise HTTPException(404, JOB_NOT_FOUND)
        return found

    async def list_jobs(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[SeoJobRecord]:
        return await seo_jobs.list(db, site_id, paging)

    async def finish_job(
        self, db: AsyncSession, site_id: str, job_id: str, body: SeoJobUpdateRequest
    ) -> SeoJobRecord:
        updated = await seo_jobs.update_status(db, site_id, job_id, body.status)
        if updated is None:
            raise HTTPException(404, JOB_NOT_FOUND)
        return updated

    async def list_page_facts(
        self, db: AsyncSession, site_id: str, paging: PaginationParams, live: bool | None
    ) -> PaginatedApiResponse[PageFactsRecord]:
        return await seo_page_facts.list(db, site_id, paging, live)

    async def page_keywords(
        self, db: AsyncSession, site_id: str, page_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[KeywordGscPageRecord]:
        return await seo_keyword_gsc_pages.list_for_page(db, site_id, page_id, paging)

    async def list_keywords(
        self, db: AsyncSession, site_id: str, f: KeywordFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[KeywordRecord]:
        return await seo_keywords.list(db, site_id, f, paging)

    async def get_keyword(self, db: AsyncSession, site_id: str, keyword_id: str) -> KeywordRecord:
        found = await seo_keywords.get(db, site_id, keyword_id)
        if found is None:
            raise HTTPException(404, KEYWORD_NOT_FOUND)
        return found

    async def keyword_pages(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> tuple[list[KeywordGscPageRecord], list[KeywordContentPageRecord]]:
        await self.get_keyword(db, site_id, keyword_id)
        return (
            await seo_keyword_gsc_pages.list_for_keyword(db, site_id, keyword_id),
            await seo_keyword_content_pages.list_for_keyword(db, site_id, keyword_id),
        )

    async def add_keywords(
        self, db: AsyncSession, user_id: str, site_id: str, keywords: list[str], source: str
    ) -> list[str]:
        await seo_site_states.ensure(db, user_id, site_id)
        await seo_keywords.insert_many(db, user_id, site_id, keywords, source)
        await seo_embed_service.embed_pending(db, user_id, site_id)
        ids = await seo_keywords.ids_for(db, site_id, keywords)
        return [ids[k] for k in keywords if k in ids]

    async def list_clusters(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[ClusterRecord]:
        return await seo_keyword_clusters.list(db, site_id, paging)

    async def list_competitors(
        self, db: AsyncSession, site_id: str, state: str | None
    ) -> list[CompetitorRecord]:
        return await seo_competitors.list(db, site_id, state)

    async def patch_competitor(
        self, db: AsyncSession, site_id: str, competitor_id: str, body: CompetitorUpdateRequest
    ) -> CompetitorRecord:
        patch = body.model_dump(exclude_none=True)
        updated = await seo_competitors.patch(db, site_id, competitor_id, patch)
        if updated is None:
            raise HTTPException(404, COMPETITOR_NOT_FOUND)
        return updated

    async def list_suggestions(
        self, db: AsyncSession, site_id: str, f: PageSuggestionFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[PageSuggestionRecord]:
        return await seo_page_suggestions.list(db, site_id, f, paging)

    async def get_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PageSuggestionRecord:
        found = await seo_page_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, SUGGESTION_NOT_FOUND)
        return found

    async def settle_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str, state: str
    ) -> PageSuggestionRecord:
        await self.get_suggestion(db, site_id, suggestion_id)
        ids = await seo_page_suggestions.pair_ids(db, site_id, suggestion_id)
        await seo_page_suggestions.set_state(db, site_id, ids, state, OPEN_STATES)
        return await self.get_suggestion(db, site_id, suggestion_id)

    async def overview(self, db: AsyncSession, user_id: str, site_id: str) -> OverviewResponse:
        state = await seo_site_states.ensure(db, user_id, site_id)
        return OverviewResponse(
            keywords=await seo_keywords.count(db, site_id),
            keywords_with_facts=await seo_keywords.count(db, site_id, with_facts=True),
            clusters=await seo_keyword_clusters.count(db, site_id),
            competitors_confirmed=await seo_competitors.count(db, site_id, "confirmed"),
            suggestions=await seo_page_suggestions.summary(db, site_id),
            state=state,
        )

    async def propose_page_edits(
        self, db: AsyncSession, user_id: str, site_id: str, body: PageEditsRequest
    ) -> CreateResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_generator_service.propose_page_edits(
            db,
            user_id,
            site_id,
            body.job_id,
            body.evidence,
            body.page_ids,
            body.keyword_ids,
            body.min_position,
            body.max_position,
            body.min_impressions,
            body.min_questions,
            body.min_drop,
        )

    async def propose_cannibalisation(
        self, db: AsyncSession, user_id: str, site_id: str, body: CannibalisationRequest
    ) -> CreateResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_generator_service.propose_cannibalisation(
            db, user_id, site_id, body.job_id, body.page_ids, body.min_shared_impressions
        )

    async def screen_suggestions(
        self, db: AsyncSession, user_id: str, site_id: str, body: ScreenRequest
    ) -> ScreenResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_screening_service.screen(
            db, user_id, site_id, body.job_id, body.ids, body.question, body.limit
        )

    async def review_inputs(
        self, db: AsyncSession, site_id: str, body: ReviewInputsRequest
    ) -> ReviewBatch:
        await self.get_job(db, site_id, body.job_id)
        return await seo_review_service.review_inputs(
            db, site_id, body.job_id, body.prompt, body.ids, body.limit
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, body: VerdictRequest
    ) -> ReviewResult:
        return await seo_review_service.apply_verdicts(db, site_id, body.verdicts)

    async def rank_suggestions(
        self, db: AsyncSession, site_id: str, body: RankRequest
    ) -> RankResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_ranking_service.rank(
            db,
            site_id,
            body.job_id,
            {"add": body.budget_add, "edit": body.budget_edit, "delete": body.budget_delete},
        )

    async def collect_keywords(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectKeywordsRequest
    ) -> CollectResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_collect_service.collect_keywords(
            db,
            user_id,
            site_id,
            body.job_id,
            body.seeds,
            body.keyword_ids,
            body.source_table,
            body.from_gsc,
            body.from_ranked,
            body.max_seeds,
            body.ideas_per_seed,
            body.dry_run,
        )

    async def collect_competitors(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectCompetitorsRequest
    ) -> CollectResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_collect_service.collect_competitors(
            db, user_id, site_id, body.job_id, body.limit, body.keyword_ids
        )

    async def collect_competitor_keywords(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectCompetitorKeywordsRequest
    ) -> CollectResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_collect_service.collect_competitor_keywords(
            db, user_id, site_id, body.job_id, body.competitor_ids, body.limit
        )

    async def collect_serps(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectSerpsRequest
    ) -> CollectResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_collect_service.collect_serps(
            db,
            user_id,
            site_id,
            body.job_id,
            body.keyword_ids,
            body.terms,
            body.suggestion_ids,
            body.source_table,
            body.device,
            body.max_keywords,
        )

    async def propose_gap_pages(
        self, db: AsyncSession, user_id: str, site_id: str, body: GapPagesRequest
    ) -> CreateResult:
        await self.get_job(db, site_id, body.job_id)
        return await seo_gap_service.propose_gap_pages(
            db,
            user_id,
            site_id,
            body.job_id,
            body.keyword_ids,
            body.min_volume,
            body.max_difficulty,
        )

    async def propose_topic_pages(
        self, db: AsyncSession, user_id: str, site_id: str, body: TopicPagesRequest
    ) -> TopicPagesResult:
        await self.get_job(db, site_id, body.job_id)
        result, collected = await seo_gap_service.propose_topic_pages(
            db,
            user_id,
            site_id,
            body.job_id,
            body.topic,
            body.source_table,
            body.ideas_per_seed,
            body.dry_run,
        )
        return TopicPagesResult(suggestions=result, collected=collected)

    async def export(
        self, db: AsyncSession, site_id: str, schema: str, dataset: str
    ) -> tuple[Path, int]:
        if dataset not in DATASETS:
            raise HTTPException(400, f"Unknown dataset. One of: {', '.join(DATASETS)}.")
        return await seo_export_service.write_csv(db, site_id, schema, dataset)


seo_service = SeoService()
