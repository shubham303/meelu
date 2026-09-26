from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.site_structure.pillars.service import pillar_page_suggestion_service
from src.site_structure.schemas import (
    HierarchyRequest,
    HierarchyResult,
    LinkSuggestionCreateRequest,
    LinkSuggestionDeleteResponse,
    LinkSuggestionFilter,
    LinkSuggestionResponse,
    LinkSuggestionSummaryResponse,
    LinkSuggestionUpdateRequest,
    MentionsRequest,
    MentionsResult,
    PillarPageSuggestionDeleteResponse,
    PillarPageSuggestionFilter,
    PillarPageSuggestionResponse,
    PillarPageSuggestionSummaryResponse,
    PillarPageSuggestionUpdateRequest,
    PillarRankRequest,
    PillarReviewInputsRequest,
    PillarScreenRequest,
    PillarsRequest,
    PillarsResult,
    PillarVerdictRequest,
    RankRequest,
    RankResult,
    ReconcileResult,
    RemovalsRequest,
    RemovalsResult,
    ReviewBatch,
    ReviewInputsRequest,
    ReviewResult,
    ScreenRequest,
    ScreenResult,
    StructureJobCreateRequest,
    StructureJobResponse,
    StructureJobUpdateRequest,
    VerdictRequest,
    fields,
)
from src.site_structure.service import link_suggestion_service, structure_job_service

router = APIRouter(prefix="/site/structure")


class StartedJobResponse(StructureJobResponse):
    reconciled: ReconcileResult


def _sort(sort_by: str | None, sort_order: str | None) -> dict[str, str]:
    try:
        return {
            "sort_by": "score" if fields.blank(sort_by) else fields.sort_by(sort_by),
            "sort_order": "desc" if fields.blank(sort_order) else fields.sort_order(sort_order),
        }
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


def link_suggestion_filter(
    state: str | None = Query("ready"),
    action: str | None = Query(None),
    job_id: str | None = Query(None, alias="jobId"),
    from_page_id: str | None = Query(None, alias="fromPageId"),
    to_page_id: str | None = Query(None, alias="toPageId"),
    page_id: str | None = Query(None, alias="pageId"),
    url: str | None = Query(None),
    sort_by: str | None = Query("score", alias="sortBy"),
    sort_order: str | None = Query("desc", alias="sortOrder"),
) -> LinkSuggestionFilter:
    return LinkSuggestionFilter(
        state=None if fields.blank(state) or state == "any" else fields.state(state),
        action=None if fields.blank(action) else fields.action(action),
        job_id=job_id or None,
        from_page_id=from_page_id or None,
        to_page_id=to_page_id or None,
        page_id=page_id or None,
        url=(url or "").strip() or None,
        **_sort(sort_by, sort_order),
    )


@router.post("/jobs", status_code=201)
async def start_job(
    body: StructureJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StartedJobResponse:
    job, reconciled = await structure_job_service.start_job(db, ctx.user_id, ctx.site_id, body)
    return StartedJobResponse(**job.model_dump(), reconciled=reconciled)


@router.get("/jobs")
async def list_jobs(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[StructureJobResponse]:
    page = await structure_job_service.list_jobs(db, ctx.site_id, paging)
    return PaginatedApiResponse[StructureJobResponse](
        data=[StructureJobResponse.model_validate(r) for r in page.data],
        pagination=page.pagination,
    )


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StructureJobResponse:
    return StructureJobResponse.model_validate(
        await structure_job_service.get_job(db, ctx.site_id, job_id)
    )


@router.patch("/jobs/{job_id}")
async def finish_job(
    job_id: str,
    body: StructureJobUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> StructureJobResponse:
    return StructureJobResponse.model_validate(
        await structure_job_service.finish_job(db, ctx.site_id, job_id, body)
    )


@router.post("/link-suggestions/reconcile")
async def reconcile(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReconcileResult:
    return await link_suggestion_service.reconcile(db, ctx.site_id)


@router.post("/link-suggestions/mentions")
async def propose_unlinked_mentions(
    body: MentionsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> MentionsResult:
    return await link_suggestion_service.propose_unlinked_mentions(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/link-suggestions/hierarchy")
async def propose_hierarchy_links(
    body: HierarchyRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> HierarchyResult:
    return await link_suggestion_service.propose_hierarchy_links(db, ctx.user_id, ctx.site_id, body)


@router.post("/link-suggestions/removals")
async def propose_link_removals(
    body: RemovalsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RemovalsResult:
    return await link_suggestion_service.propose_link_removals(db, ctx.user_id, ctx.site_id, body)


@router.post("/link-suggestions/screen")
async def screen_link_suggestions(
    body: ScreenRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ScreenResult:
    return await link_suggestion_service.screen_suggestions(db, ctx.user_id, ctx.site_id, body)


@router.post("/link-suggestions/review-inputs")
async def link_suggestion_review_inputs(
    body: ReviewInputsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewBatch:
    return await link_suggestion_service.review_inputs(db, ctx.site_id, body)


@router.post("/link-suggestions/verdicts")
async def link_suggestion_verdicts(
    body: VerdictRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewResult:
    return await link_suggestion_service.apply_verdicts(db, ctx.site_id, body)


@router.post("/link-suggestions/rank")
async def rank_link_suggestions(
    body: RankRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankResult:
    return await link_suggestion_service.rank_suggestions(db, ctx.site_id, body)


@router.get("/link-suggestions/summary")
async def link_suggestion_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionSummaryResponse:
    return await link_suggestion_service.summary(db, ctx.site_id)


@router.get("/link-suggestions")
async def list_link_suggestions(
    filters: LinkSuggestionFilter = Depends(link_suggestion_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[LinkSuggestionResponse]:
    page = await link_suggestion_service.list_suggestions(db, ctx.site_id, filters, paging)
    return PaginatedApiResponse[LinkSuggestionResponse](
        data=[LinkSuggestionResponse.model_validate(r) for r in page.data],
        pagination=page.pagination,
    )


@router.post("/link-suggestions", status_code=201)
async def create_link_suggestion(
    body: LinkSuggestionCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionResponse:
    record = await link_suggestion_service.create_suggestion(db, ctx.user_id, ctx.site_id, body)
    return LinkSuggestionResponse.model_validate(record)


@router.get("/link-suggestions/{suggestion_id}")
async def get_link_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionResponse:
    return LinkSuggestionResponse.model_validate(
        await link_suggestion_service.get_suggestion(db, ctx.site_id, suggestion_id)
    )


@router.patch("/link-suggestions/{suggestion_id}")
async def update_link_suggestion(
    suggestion_id: str,
    body: LinkSuggestionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionResponse:
    record = await link_suggestion_service.update_suggestion(db, ctx.site_id, suggestion_id, body)
    return LinkSuggestionResponse.model_validate(record)


@router.delete("/link-suggestions/{suggestion_id}")
async def delete_link_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionDeleteResponse:
    record = await link_suggestion_service.delete_suggestion(db, ctx.site_id, suggestion_id)
    return LinkSuggestionDeleteResponse(id=record.id)


def pillar_filter(
    state: str | None = Query("ready"),
    action: str | None = Query(None),
    job_id: str | None = Query(None, alias="jobId"),
    sort_by: str | None = Query("score", alias="sortBy"),
    sort_order: str | None = Query("desc", alias="sortOrder"),
) -> PillarPageSuggestionFilter:
    return PillarPageSuggestionFilter(
        state=None if fields.blank(state) or state == "any" else fields.state(state),
        action=None if fields.blank(action) else fields.pillar_action(action),
        job_id=job_id or None,
        **_sort(sort_by, sort_order),
    )


@router.post("/pillar-suggestions/propose")
async def propose_pillar_pages(
    body: PillarsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarsResult:
    return await pillar_page_suggestion_service.propose_pillar_pages(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/pillar-suggestions/screen")
async def screen_pillar_suggestions(
    body: PillarScreenRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ScreenResult:
    return await pillar_page_suggestion_service.screen_suggestions(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/pillar-suggestions/review-inputs")
async def pillar_suggestion_review_inputs(
    body: PillarReviewInputsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewBatch:
    return await pillar_page_suggestion_service.review_inputs(db, ctx.site_id, body)


@router.post("/pillar-suggestions/verdicts")
async def pillar_suggestion_verdicts(
    body: PillarVerdictRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewResult:
    return await pillar_page_suggestion_service.apply_verdicts(db, ctx.site_id, body)


@router.post("/pillar-suggestions/rank")
async def rank_pillar_suggestions(
    body: PillarRankRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankResult:
    return await pillar_page_suggestion_service.rank_suggestions(db, ctx.site_id, body)


@router.get("/pillar-suggestions/summary")
async def pillar_suggestion_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionSummaryResponse:
    return await pillar_page_suggestion_service.summary(db, ctx.site_id)


@router.get("/pillar-suggestions")
async def list_pillar_suggestions(
    filters: PillarPageSuggestionFilter = Depends(pillar_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PillarPageSuggestionResponse]:
    page = await pillar_page_suggestion_service.list_suggestions(db, ctx.site_id, filters, paging)
    return PaginatedApiResponse[PillarPageSuggestionResponse](
        data=[PillarPageSuggestionResponse.model_validate(r) for r in page.data],
        pagination=page.pagination,
    )


@router.get("/pillar-suggestions/{suggestion_id}")
async def get_pillar_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionResponse:
    return PillarPageSuggestionResponse.model_validate(
        await pillar_page_suggestion_service.get_suggestion(db, ctx.site_id, suggestion_id)
    )


@router.patch("/pillar-suggestions/{suggestion_id}")
async def update_pillar_suggestion(
    suggestion_id: str,
    body: PillarPageSuggestionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionResponse:
    return PillarPageSuggestionResponse.model_validate(
        await pillar_page_suggestion_service.update_suggestion(db, ctx.site_id, suggestion_id, body)
    )


@router.delete("/pillar-suggestions/{suggestion_id}")
async def delete_pillar_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionDeleteResponse:
    record = await pillar_page_suggestion_service.delete_suggestion(db, ctx.site_id, suggestion_id)
    return PillarPageSuggestionDeleteResponse(id=record.id)
