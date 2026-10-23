from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.find_leads.schemas import (
    BriefCreateRequest,
    BriefPatchRequest,
    BriefResponse,
    CandidatesRequest,
    CheckRequest,
    CheckResponse,
    CollectRequest,
    DeleteResponse,
    InsertedResponse,
    JudgeRequest,
    LeadFilters,
    LeadPatchRequest,
    LeadResponse,
    RunCreateRequest,
    RunResponse,
    RunUpdateRequest,
    SearchResponse,
    SummaryResponse,
    VerdictResponse,
    WebSearchRecord,
)
from src.find_leads.service import find_leads_service

router = APIRouter()


@router.get("/find-leads/briefs")
async def list_briefs(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[BriefResponse]:
    return await find_leads_service.list_briefs(db, ctx.site_id)


@router.post("/find-leads/briefs", status_code=201)
async def create_brief(
    body: BriefCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BriefResponse:
    return await find_leads_service.create_brief(db, ctx.user_id, ctx.site_id, body)


@router.get("/find-leads/briefs/{brief_id}")
async def get_brief(
    brief_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BriefResponse:
    return await find_leads_service.get_brief(db, ctx.site_id, brief_id)


@router.patch("/find-leads/briefs/{brief_id}")
async def patch_brief(
    brief_id: str,
    body: BriefPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BriefResponse:
    return await find_leads_service.patch_brief(db, ctx.site_id, brief_id, body)


@router.delete("/find-leads/briefs/{brief_id}")
async def delete_brief(
    brief_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await find_leads_service.delete_brief(db, ctx.site_id, brief_id))


@router.post("/find-leads/runs", status_code=201)
async def create_run(
    body: RunCreateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await find_leads_service.create_run(
        db, ctx.user_id, ctx.site_id, body or RunCreateRequest()
    )


@router.get("/find-leads/runs")
async def list_runs(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[RunResponse]:
    return await find_leads_service.list_runs(db, ctx.site_id, paging)


@router.get("/find-leads/runs/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await find_leads_service.get_run(db, ctx.site_id, run_id)


@router.patch("/find-leads/runs/{run_id}")
async def patch_run(
    run_id: str,
    body: RunUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await find_leads_service.patch_run(db, ctx.site_id, run_id, body)


@router.post("/find-leads/runs/{run_id}/collect")
async def start_collect(
    run_id: str,
    body: CollectRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await find_leads_service.start_collect(
        db, ctx.user_id, ctx.site_id, run_id, body.source, body.platform, body.searches
    )


@router.post("/find-leads/runs/{run_id}/screen")
async def start_screen(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await find_leads_service.start_screen(db, ctx.user_id, ctx.site_id, run_id)


@router.post("/find-leads/runs/{run_id}/enrich")
async def start_enrich(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await find_leads_service.start_enrich(db, ctx.user_id, ctx.site_id, run_id)


@router.post("/find-leads/leads/candidates")
async def add_candidates(
    body: CandidatesRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> InsertedResponse:
    return await find_leads_service.add_candidates(db, ctx.user_id, ctx.site_id, body)


@router.post("/find-leads/leads/judged")
async def judge_leads(
    body: JudgeRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> VerdictResponse:
    return await find_leads_service.judge(db, ctx.user_id, ctx.site_id, body)


@router.post("/find-leads/leads/check")
async def check_leads(
    body: CheckRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CheckResponse:
    return await find_leads_service.check(db, ctx.user_id, ctx.site_id, body)


@router.get("/find-leads/searches")
async def list_searches(
    platform: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[SearchResponse]:
    return await find_leads_service.list_searches(db, ctx.site_id, platform)


@router.put("/find-leads/searches/web")
async def record_web_search(
    body: WebSearchRecord,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SearchResponse:
    return await find_leads_service.record_web_search(db, ctx.user_id, ctx.site_id, body)


@router.get("/find-leads/leads")
async def list_leads(
    status: str | None = Query(None),
    brief_id: str | None = Query(None, alias="briefId"),
    run_id: str | None = Query(None, alias="runId"),
    source: str | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[LeadResponse]:
    filters = LeadFilters(
        statuses=[s for s in (status or "").split(",") if s] or None,
        brief_id=brief_id,
        run_id=run_id,
        source=source,
        q=q,
    )
    return await find_leads_service.list_leads(db, ctx.site_id, filters, paging)


@router.get("/find-leads/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SummaryResponse:
    return await find_leads_service.summary(db, ctx.user_id, ctx.site_id)


@router.get("/find-leads/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LeadResponse:
    return await find_leads_service.get_lead(db, ctx.site_id, lead_id)


@router.patch("/find-leads/leads/{lead_id}")
async def patch_lead(
    lead_id: str,
    body: LeadPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> LeadResponse:
    return await find_leads_service.patch_lead(db, ctx.site_id, lead_id, body)


@router.delete("/find-leads/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(
        id=await find_leads_service.delete_lead(db, ctx.user_id, ctx.site_id, lead_id)
    )
