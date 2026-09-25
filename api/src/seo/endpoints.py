from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.core.schemas import EntityModel
from src.seo import export, service
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
    fields,
)

router = APIRouter(prefix="/seo")


class StartedJobResponse(SeoJobRecord):
    reconciled: ReconcileResult


class KeywordPagesResponse(EntityModel):
    gsc: list[KeywordGscPageRecord]
    content: list[KeywordContentPageRecord]


def keyword_filter(
    source: str | None = Query(None),
    cluster_id: str | None = Query(None, alias="clusterId"),
    branded: bool | None = Query(None),
    has_facts: bool | None = Query(None, alias="hasFacts"),
    search: str | None = Query(None),
) -> KeywordFilter:
    return KeywordFilter(
        source=source or None,
        cluster_id=cluster_id or None,
        branded=branded,
        has_facts=has_facts,
        search=(search or "").strip() or None,
    )


def suggestion_filter(
    state: str | None = Query("ready"),
    action: str | None = Query(None),
    job_id: str | None = Query(None, alias="jobId"),
    page_id: str | None = Query(None, alias="pageId"),
    topic_key: str | None = Query(None, alias="topicKey"),
) -> PageSuggestionFilter:
    return PageSuggestionFilter(
        state=None if fields.blank(state) or state == "any" else fields.state(state),
        action=None if fields.blank(action) else fields.action(action),
        job_id=job_id or None,
        page_id=page_id or None,
        topic_key=topic_key or None,
    )


@router.get("/state")
async def get_state(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> SiteStateRecord:
    return await service.get_state(db, ctx.user_id, ctx.site_id)


@router.patch("/state")
async def patch_state(
    body: SiteStateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteStateRecord:
    return await service.patch_state(db, ctx.user_id, ctx.site_id, body)


@router.post("/rollup")
async def run_rollup(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> RollupResult:
    return await service.run_rollup(db, ctx.user_id, ctx.site_id)


@router.post("/precompute")
async def request_precompute(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> SiteStateRecord:
    return await service.request_precompute(db, ctx.user_id, ctx.site_id)


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> OverviewResponse:
    return await service.overview(db, ctx.user_id, ctx.site_id)


@router.post("/jobs", status_code=201)
async def start_job(
    body: SeoJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StartedJobResponse:
    job, reconciled = await service.start_job(db, ctx.user_id, ctx.site_id, body)
    return StartedJobResponse(**job.model_dump(), reconciled=reconciled)


@router.get("/jobs")
async def list_jobs(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[SeoJobRecord]:
    return await service.list_jobs(db, ctx.site_id, paging)


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str, db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> SeoJobRecord:
    return await service.get_job(db, ctx.site_id, job_id)


@router.patch("/jobs/{job_id}")
async def finish_job(
    job_id: str,
    body: SeoJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SeoJobRecord:
    return await service.finish_job(db, ctx.site_id, job_id, body)


@router.get("/pages")
async def list_page_facts(
    live: bool | None = Query(None),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PageFactsRecord]:
    return await service.list_page_facts(db, ctx.site_id, paging, live)


@router.get("/pages/{page_id}/keywords")
async def page_keywords(
    page_id: str,
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[KeywordGscPageRecord]:
    return await service.page_keywords(db, ctx.site_id, page_id, paging)


@router.get("/keywords")
async def list_keywords(
    f: KeywordFilter = Depends(keyword_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[KeywordRecord]:
    return await service.list_keywords(db, ctx.site_id, f, paging)


@router.get("/keywords/{keyword_id}")
async def get_keyword(
    keyword_id: str, db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> KeywordRecord:
    return await service.get_keyword(db, ctx.site_id, keyword_id)


@router.get("/keywords/{keyword_id}/pages")
async def keyword_pages(
    keyword_id: str, db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> KeywordPagesResponse:
    gsc, content = await service.keyword_pages(db, ctx.site_id, keyword_id)
    return KeywordPagesResponse(gsc=gsc, content=content)


@router.get("/clusters")
async def list_clusters(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[ClusterRecord]:
    return await service.list_clusters(db, ctx.site_id, paging)


@router.get("/competitors")
async def list_competitors(
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[CompetitorRecord]:
    return await service.list_competitors(
        db, ctx.site_id, None if fields.blank(state) else fields.competitor_state(state)
    )


@router.patch("/competitors/{competitor_id}")
async def patch_competitor(
    competitor_id: str,
    body: CompetitorUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CompetitorRecord:
    return await service.patch_competitor(db, ctx.site_id, competitor_id, body)


@router.get("/page-suggestions")
async def list_suggestions(
    f: PageSuggestionFilter = Depends(suggestion_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PageSuggestionRecord]:
    return await service.list_suggestions(db, ctx.site_id, f, paging)


@router.post("/page-suggestions", status_code=201)
async def save_suggestion(
    body: SavePageSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await service.save_suggestion(db, ctx.user_id, ctx.site_id, body)


@router.post("/reconcile")
async def reconcile(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> ReconcileResult:
    return await service.reconcile(db, ctx.user_id, ctx.site_id)


@router.get("/page-suggestions/{suggestion_id}")
async def get_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageSuggestionRecord:
    return await service.get_suggestion(db, ctx.site_id, suggestion_id)


@router.post("/page-suggestions/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageSuggestionRecord:
    return await service.settle_suggestion(db, ctx.site_id, suggestion_id, "user_rejected")


@router.post("/page-suggestions/{suggestion_id}/done")
async def done_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageSuggestionRecord:
    return await service.settle_suggestion(db, ctx.site_id, suggestion_id, "done")


@router.post("/page-suggestions/propose-edits")
async def propose_page_edits(
    body: PageEditsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await service.propose_page_edits(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/propose-cannibalisation")
async def propose_cannibalisation(
    body: CannibalisationRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await service.propose_cannibalisation(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/screen")
async def screen_suggestions(
    body: ScreenRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ScreenResult:
    return await service.screen_suggestions(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/review-inputs")
async def page_suggestion_review_inputs(
    body: ReviewInputsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewBatch:
    return await service.review_inputs(db, ctx.site_id, body)


@router.post("/page-suggestions/verdicts")
async def page_suggestion_verdicts(
    body: VerdictRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewResult:
    return await service.apply_verdicts(db, ctx.site_id, body)


@router.post("/page-suggestions/rank")
async def rank_suggestions(
    body: RankRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankResult:
    return await service.rank_suggestions(db, ctx.site_id, body)


@router.post("/collect/keywords")
async def collect_keywords(
    body: CollectKeywordsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await service.collect_keywords(db, ctx.user_id, ctx.site_id, body)


@router.post("/collect/competitors")
async def collect_competitors(
    body: CollectCompetitorsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await service.collect_competitors(db, ctx.user_id, ctx.site_id, body)


@router.post("/collect/competitor-keywords")
async def collect_competitor_keywords(
    body: CollectCompetitorKeywordsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await service.collect_competitor_keywords(db, ctx.user_id, ctx.site_id, body)


@router.post("/collect/serps")
async def collect_serps(
    body: CollectSerpsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CollectResult:
    return await service.collect_serps(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/propose-gaps")
async def propose_gap_pages(
    body: GapPagesRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await service.propose_gap_pages(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/propose-topic")
async def propose_topic_pages(
    body: TopicPagesRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TopicPagesResult:
    return await service.propose_topic_pages(db, ctx.user_id, ctx.site_id, body)


@router.get("/export")
async def export_dataset(
    dataset: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> dict:
    if dataset not in export.DATASETS:
        raise HTTPException(400, f"Unknown dataset. One of: {', '.join(export.DATASETS)}.")
    _, schema = tenant_names(ctx.user_id)
    path, rows = await export.write_csv(db, ctx.site_id, schema, dataset)
    return {"path": str(path), "rows": rows, "dataset": dataset}
