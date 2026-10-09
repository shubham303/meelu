from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.site_structure.links.schemas import (
    HierarchyRequest,
    HierarchyResult,
    LinkAction,
    LinkSortBy,
    LinkSuggestionCreateRequest,
    LinkSuggestionDeleteResponse,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    LinkSuggestionUpdateRequest,
    MentionsRequest,
    MentionsResult,
    PairsRequest,
    PairsResult,
    RankRequest,
    ReconcileResult,
    RemovalsRequest,
    RemovalsResult,
    ReviewInputsRequest,
    ScreenRequest,
    SortOrder,
    VerdictRequest,
)
from src.site_structure.links.service import link_suggestion_service
from src.site_structure.pipeline.schemas import RankResult, ReviewBatch, ReviewResult, ScreenResult
from src.site_structure.schemas import fields

router = APIRouter(prefix="/link-suggestions")


def link_suggestion_filter(
    state: list[str] | None = Query(None),
    action: LinkAction | None = Query(None),
    job_id: str | None = Query(None, alias="jobId"),
    from_page_id: str | None = Query(None, alias="fromPageId"),
    to_page_id: str | None = Query(None, alias="toPageId"),
    page_id: str | None = Query(None, alias="pageId"),
    from_url: str | None = Query(None, alias="fromUrl"),
    to_url: str | None = Query(None, alias="toUrl"),
    url: str | None = Query(None),
    sort_by: LinkSortBy = Query(LinkSortBy.SCORE, alias="sortBy"),
    sort_order: SortOrder = Query(SortOrder.DESC, alias="sortOrder"),
) -> LinkSuggestionFilter:
    try:
        states = fields.states(state)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return LinkSuggestionFilter(
        states=states,
        action=action,
        job_id=job_id or None,
        from_page_id=from_page_id or None,
        to_page_id=to_page_id or None,
        page_id=page_id or None,
        from_url=(from_url or "").strip() or None,
        to_url=(to_url or "").strip() or None,
        url=(url or "").strip() or None,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/reconcile")
async def reconcile_link_suggestions(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReconcileResult:
    return await link_suggestion_service.reconcile(db, ctx.site_id)


@router.post("/hierarchy")
async def propose_hierarchy_links(
    body: HierarchyRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> HierarchyResult:
    return await link_suggestion_service.add_hierarchy_edges(db, ctx.user_id, ctx.site_id, body)


@router.post("/mentions")
async def propose_unlinked_mentions(
    body: MentionsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> MentionsResult:
    return await link_suggestion_service.propose_unlinked_mentions(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/removals")
async def propose_link_removals(
    body: RemovalsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RemovalsResult:
    return await link_suggestion_service.propose_link_removals(db, ctx.user_id, ctx.site_id, body)


@router.post("/from-table")
async def propose_links_from_table(
    body: PairsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PairsResult:
    return await link_suggestion_service.propose_links_from_table(
        db, ctx.user_id, ctx.site_id, body
    )


@router.post("/screen")
async def screen_link_suggestions(
    body: ScreenRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ScreenResult:
    return await link_suggestion_service.screen_suggestions(db, ctx.user_id, ctx.site_id, body)


@router.post("/review-inputs")
async def link_suggestion_review_inputs(
    body: ReviewInputsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewBatch:
    return await link_suggestion_service.review_inputs(db, ctx.site_id, body)


@router.post("/verdicts")
async def link_suggestion_verdicts(
    body: VerdictRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ReviewResult:
    return await link_suggestion_service.apply_verdicts(db, ctx.site_id, body)


@router.post("/rank")
async def rank_link_suggestions(
    body: RankRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RankResult:
    return await link_suggestion_service.rank_suggestions(db, ctx.site_id, body)


@router.get("/summary")
async def link_suggestion_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionSummaryResponse:
    return await link_suggestion_service.summary(db, ctx.site_id)


@router.get("")
async def list_link_suggestions(
    filters: LinkSuggestionFilter = Depends(link_suggestion_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[LinkSuggestionRecord]:
    return await link_suggestion_service.list(db, ctx.site_id, filters, paging)


@router.post("", status_code=201)
async def create_link_suggestion(
    body: LinkSuggestionCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionRecord:
    return await link_suggestion_service.create(db, ctx.user_id, ctx.site_id, body)


@router.get("/{suggestion_id}")
async def get_link_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionRecord:
    return await link_suggestion_service.get(db, ctx.site_id, suggestion_id)


@router.patch("/{suggestion_id}")
async def update_link_suggestion(
    suggestion_id: str,
    body: LinkSuggestionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionRecord:
    return await link_suggestion_service.update(db, ctx.site_id, suggestion_id, body)


@router.delete("/{suggestion_id}")
async def delete_link_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LinkSuggestionDeleteResponse:
    record = await link_suggestion_service.delete(db, ctx.site_id, suggestion_id)
    return LinkSuggestionDeleteResponse(id=record.id)
