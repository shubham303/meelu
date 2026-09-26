from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.site_structure.constants import PillarAction
from src.site_structure.pillars.schemas import (
    PillarPageSuggestionCreateRequest,
    PillarPageSuggestionDeleteResponse,
    PillarPageSuggestionFilter,
    PillarPageSuggestionRecord,
    PillarPageSuggestionSummaryResponse,
    PillarPageSuggestionUpdateRequest,
    PillarRankRequest,
    PillarReviewInputsRequest,
    PillarScreenRequest,
    PillarSortBy,
    PillarsRequest,
    PillarsResult,
    PillarVerdictRequest,
    ReconcileResult,
    SortOrder,
)
from src.site_structure.pillars.service import pillar_page_suggestion_service
from src.site_structure.pipeline.schemas import RankResult, ReviewBatch, ReviewResult, ScreenResult
from src.site_structure.schemas import fields

router = APIRouter(prefix="/pillar-suggestions")


def pillar_suggestion_filter(
    state: list[str] | None = Query(None),
    action: PillarAction | None = Query(None),
    job_id: str | None = Query(None, alias="jobId"),
    page_id: str | None = Query(None, alias="pageId"),
    sort_by: PillarSortBy = Query(PillarSortBy.SCORE, alias="sortBy"),
    sort_order: SortOrder = Query(SortOrder.DESC, alias="sortOrder"),
) -> PillarPageSuggestionFilter:
    try:
        states = fields.states(state)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return PillarPageSuggestionFilter(
        states=states,
        action=action,
        job_id=job_id or None,
        page_id=page_id or None,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/reconcile")
async def reconcile_pillar_suggestions(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReconcileResult:
    return await pillar_page_suggestion_service.reconcile(db, ctx.site_id)


@router.post("/propose")
async def propose_pillar_pages(
    body: PillarsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarsResult:
    return await pillar_page_suggestion_service.propose_pillar_pages(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/screen")
async def screen_pillar_suggestions(
    body: PillarScreenRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ScreenResult:
    return await pillar_page_suggestion_service.screen_suggestions(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/review-inputs")
async def pillar_suggestion_review_inputs(
    body: PillarReviewInputsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewBatch:
    return await pillar_page_suggestion_service.review_inputs(db, ctx.site_id, body)


@router.post("/verdicts")
async def pillar_suggestion_verdicts(
    body: PillarVerdictRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewResult:
    return await pillar_page_suggestion_service.apply_verdicts(db, ctx.site_id, body)


@router.post("/rank")
async def rank_pillar_suggestions(
    body: PillarRankRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankResult:
    return await pillar_page_suggestion_service.rank_suggestions(db, ctx.site_id, body)


@router.get("/summary")
async def pillar_suggestion_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionSummaryResponse:
    return await pillar_page_suggestion_service.summary(db, ctx.site_id)


@router.get("")
async def list_pillar_suggestions(
    filters: PillarPageSuggestionFilter = Depends(pillar_suggestion_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
    return await pillar_page_suggestion_service.list(db, ctx.site_id, filters, paging)


@router.post("", status_code=201)
async def create_pillar_suggestion(
    body: PillarPageSuggestionCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionRecord:
    return await pillar_page_suggestion_service.create(db, ctx.user_id, ctx.site_id, body)


@router.get("/{suggestion_id}")
async def get_pillar_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionRecord:
    return await pillar_page_suggestion_service.get(db, ctx.site_id, suggestion_id)


@router.patch("/{suggestion_id}")
async def update_pillar_suggestion(
    suggestion_id: str,
    body: PillarPageSuggestionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionRecord:
    return await pillar_page_suggestion_service.update(db, ctx.site_id, suggestion_id, body)


@router.delete("/{suggestion_id}")
async def delete_pillar_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PillarPageSuggestionDeleteResponse:
    record = await pillar_page_suggestion_service.delete(db, ctx.site_id, suggestion_id)
    return PillarPageSuggestionDeleteResponse(id=record.id)
