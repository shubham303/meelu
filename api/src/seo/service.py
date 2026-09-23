from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo import collect, gap, generators, precompute, ranking, review, screening, suggestions
from src.seo import reconcile as reconciliation
from src.seo import repository as repo
from src.seo.constants import OPEN_STATES
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
    ReviewRequest,
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
)
from src.settings import settings

JOB_NOT_FOUND = "No such SEO job on this website."

SUGGESTION_NOT_FOUND = "No such page suggestion on this website."

COMPETITOR_NOT_FOUND = "No such competitor on this website."

KEYWORD_NOT_FOUND = "No such keyword on this website."


async def get_state(db: AsyncSession, user_id: str, site_id: str) -> SiteStateRecord:
    return await repo.ensure_state(db, user_id, site_id)


async def patch_state(
    db: AsyncSession, user_id: str, site_id: str, body: SiteStateUpdateRequest
) -> SiteStateRecord:
    await repo.ensure_state(db, user_id, site_id)
    patch = body.model_dump(exclude_none=True)
    if not patch:
        return await repo.ensure_state(db, user_id, site_id)
    updated = await repo.patch_state(db, site_id, patch)
    if "brand_terms" in patch:
        await precompute.rollup.mark_branded(db, site_id, patch["brand_terms"])
    return updated


async def run_rollup(db: AsyncSession, user_id: str, site_id: str) -> RollupResult:
    await repo.ensure_state(db, user_id, site_id)
    result = await precompute.run_rollup(db, user_id, site_id)
    await db.commit()
    return result


async def request_precompute(db: AsyncSession, user_id: str, site_id: str) -> SiteStateRecord:
    await repo.ensure_state(db, user_id, site_id)
    await precompute.request_rebuild(db, site_id)
    found = await repo.get_state(db, site_id)
    assert found is not None
    return found


async def reconcile(db: AsyncSession, user_id: str, site_id: str) -> ReconcileResult:
    state = await repo.ensure_state(db, user_id, site_id)
    pending = state.embedded_at is None or (
        state.precompute_requested_at is not None
        and state.precompute_requested_at > state.embedded_at
    )
    return await reconciliation.reconcile(db, site_id, pending)


async def save_suggestion(
    db: AsyncSession, user_id: str, site_id: str, body: SavePageSuggestionRequest
) -> CreateResult:
    await get_job(db, site_id, body.job_id)
    keyword_ids = list(body.keyword_ids)
    if body.terms:
        keyword_ids += await add_keywords(db, user_id, site_id, body.terms, "user")
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
    return await suggestions.create_many(db, user_id, site_id, body.job_id, [new])


async def start_job(
    db: AsyncSession, user_id: str, site_id: str, body: SeoJobCreateRequest
) -> tuple[SeoJobRecord, ReconcileResult]:
    await repo.ensure_state(db, user_id, site_id)
    await repo.fail_running_jobs(db, site_id)
    await precompute.run_rollup(db, user_id, site_id)
    reconciled = await reconcile(db, user_id, site_id)
    job = await repo.create_job(
        db, user_id, site_id, body.prompt, settings.seo_job_vendor_ceiling_micros
    )
    return job, reconciled


async def get_job(db: AsyncSession, site_id: str, job_id: str) -> SeoJobRecord:
    found = await repo.get_job(db, site_id, job_id)
    if found is None:
        raise HTTPException(404, JOB_NOT_FOUND)
    return found


async def list_jobs(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[SeoJobRecord]:
    return await repo.list_jobs(db, site_id, paging)


async def finish_job(
    db: AsyncSession, site_id: str, job_id: str, body: SeoJobUpdateRequest
) -> SeoJobRecord:
    updated = await repo.update_job_status(db, site_id, job_id, body.status)
    if updated is None:
        raise HTTPException(404, JOB_NOT_FOUND)
    return updated


async def list_page_facts(
    db: AsyncSession, site_id: str, paging: PaginationParams, live: bool | None
) -> PaginatedApiResponse[PageFactsRecord]:
    return await repo.list_page_facts(db, site_id, paging, live)


async def page_keywords(
    db: AsyncSession, site_id: str, page_id: str, paging: PaginationParams
) -> PaginatedApiResponse[KeywordGscPageRecord]:
    return await repo.page_gsc_keywords(db, site_id, page_id, paging)


async def list_keywords(
    db: AsyncSession, site_id: str, f: KeywordFilter, paging: PaginationParams
) -> PaginatedApiResponse[KeywordRecord]:
    return await repo.list_keywords(db, site_id, f, paging)


async def get_keyword(db: AsyncSession, site_id: str, keyword_id: str) -> KeywordRecord:
    found = await repo.get_keyword(db, site_id, keyword_id)
    if found is None:
        raise HTTPException(404, KEYWORD_NOT_FOUND)
    return found


async def keyword_pages(
    db: AsyncSession, site_id: str, keyword_id: str
) -> tuple[list[KeywordGscPageRecord], list[KeywordContentPageRecord]]:
    await get_keyword(db, site_id, keyword_id)
    return (
        await repo.keyword_gsc_pages(db, site_id, keyword_id),
        await repo.keyword_content_pages(db, site_id, keyword_id),
    )


async def add_keywords(
    db: AsyncSession, user_id: str, site_id: str, keywords: list[str], source: str
) -> list[str]:
    await repo.ensure_state(db, user_id, site_id)
    await repo.insert_keywords(db, user_id, site_id, keywords, source)
    await precompute.embed.embed_pending(db, user_id, site_id)
    ids = await repo.keyword_ids_for(db, site_id, keywords)
    return [ids[k] for k in keywords if k in ids]


async def list_clusters(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[ClusterRecord]:
    return await repo.list_clusters(db, site_id, paging)


async def list_competitors(
    db: AsyncSession, site_id: str, state: str | None
) -> list[CompetitorRecord]:
    return await repo.list_competitors(db, site_id, state)


async def patch_competitor(
    db: AsyncSession, site_id: str, competitor_id: str, body: CompetitorUpdateRequest
) -> CompetitorRecord:
    patch = body.model_dump(exclude_none=True)
    updated = await repo.patch_competitor(db, site_id, competitor_id, patch)
    if updated is None:
        raise HTTPException(404, COMPETITOR_NOT_FOUND)
    return updated


async def list_suggestions(
    db: AsyncSession, site_id: str, f: PageSuggestionFilter, paging: PaginationParams
) -> PaginatedApiResponse[PageSuggestionRecord]:
    return await repo.list_suggestions(db, site_id, f, paging)


async def get_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> PageSuggestionRecord:
    found = await repo.get_suggestion(db, site_id, suggestion_id)
    if found is None:
        raise HTTPException(404, SUGGESTION_NOT_FOUND)
    return found


async def settle_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str, state: str
) -> PageSuggestionRecord:
    await get_suggestion(db, site_id, suggestion_id)
    ids = await repo.pair_of(db, site_id, suggestion_id)
    await repo.set_suggestion_state(db, site_id, ids, state, OPEN_STATES)
    return await get_suggestion(db, site_id, suggestion_id)


async def overview(db: AsyncSession, user_id: str, site_id: str) -> OverviewResponse:
    state = await repo.ensure_state(db, user_id, site_id)
    numbers = await repo.counts(db, site_id)
    return OverviewResponse(
        **numbers, suggestions=await repo.suggestion_summary(db, site_id), state=state
    )


async def propose_page_edits(
    db: AsyncSession, user_id: str, site_id: str, body: PageEditsRequest
) -> CreateResult:
    await get_job(db, site_id, body.job_id)
    return await generators.propose_page_edits(
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
    db: AsyncSession, user_id: str, site_id: str, body: CannibalisationRequest
) -> CreateResult:
    await get_job(db, site_id, body.job_id)
    return await generators.propose_cannibalisation(
        db, user_id, site_id, body.job_id, body.page_ids, body.min_shared_impressions
    )


async def screen_suggestions(
    db: AsyncSession, user_id: str, site_id: str, body: ScreenRequest
) -> ScreenResult:
    await get_job(db, site_id, body.job_id)
    return await screening.screen(
        db, user_id, site_id, body.job_id, body.ids, body.question, body.limit
    )


async def review_suggestions(
    db: AsyncSession, user_id: str, site_id: str, body: ReviewRequest
) -> ReviewResult:
    await get_job(db, site_id, body.job_id)
    return await review.review(db, user_id, site_id, body.job_id, body.prompt, body.ids, body.limit)


async def rank_suggestions(db: AsyncSession, site_id: str, body: RankRequest) -> RankResult:
    await get_job(db, site_id, body.job_id)
    return await ranking.rank(
        db,
        site_id,
        body.job_id,
        {"add": body.budget_add, "edit": body.budget_edit, "delete": body.budget_delete},
    )


async def collect_keywords(
    db: AsyncSession, user_id: str, site_id: str, body: CollectKeywordsRequest
) -> CollectResult:
    await get_job(db, site_id, body.job_id)
    return await collect.collect_keywords(
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
    db: AsyncSession, user_id: str, site_id: str, body: CollectCompetitorsRequest
) -> CollectResult:
    await get_job(db, site_id, body.job_id)
    return await collect.collect_competitors(
        db, user_id, site_id, body.job_id, body.limit, body.keyword_ids
    )


async def collect_competitor_keywords(
    db: AsyncSession, user_id: str, site_id: str, body: CollectCompetitorKeywordsRequest
) -> CollectResult:
    await get_job(db, site_id, body.job_id)
    return await collect.collect_competitor_keywords(
        db, user_id, site_id, body.job_id, body.competitor_ids, body.limit
    )


async def collect_serps(
    db: AsyncSession, user_id: str, site_id: str, body: CollectSerpsRequest
) -> CollectResult:
    await get_job(db, site_id, body.job_id)
    return await collect.collect_serps(
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
    db: AsyncSession, user_id: str, site_id: str, body: GapPagesRequest
) -> CreateResult:
    await get_job(db, site_id, body.job_id)
    return await gap.propose_gap_pages(
        db, user_id, site_id, body.job_id, body.keyword_ids, body.min_volume, body.max_difficulty
    )


async def propose_topic_pages(
    db: AsyncSession, user_id: str, site_id: str, body: TopicPagesRequest
) -> TopicPagesResult:
    await get_job(db, site_id, body.job_id)
    result, collected = await gap.propose_topic_pages(
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
