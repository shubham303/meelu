from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.social_listening.schemas import (
    CollectRequest,
    ConfigResponse,
    ConfigUpdateRequest,
    DeleteResponse,
    EstimateResponse,
    GateResponse,
    JudgeResponse,
    PostFilters,
    PostPatchRequest,
    PostResponse,
    PostsJudgeRequest,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    RunResponse,
    RunUpdateRequest,
    SummaryResponse,
    UpsertResponse,
)
from src.social_listening.service import social_listening_service

router = APIRouter()


@router.get("/social-listening/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConfigResponse:
    return await social_listening_service.get_config(db, ctx.user_id, ctx.site_id)


@router.put("/social-listening/config")
async def put_config(
    body: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConfigResponse:
    return await social_listening_service.update_config(db, ctx.user_id, ctx.site_id, body)


@router.get("/social-listening/estimate")
async def get_estimate(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> EstimateResponse:
    return await social_listening_service.estimate(db, ctx.site_id)


@router.get("/social-listening/queries")
async def list_queries(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[QueryResponse]:
    return await social_listening_service.list_queries(db, ctx.site_id)


@router.post("/social-listening/queries")
async def upsert_queries(
    body: list[QueryUpsertItem],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> UpsertResponse:
    return await social_listening_service.upsert_queries(db, ctx.user_id, ctx.site_id, body)


@router.patch("/social-listening/queries/{query_id}")
async def patch_query(
    query_id: str,
    body: QueryPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> QueryResponse:
    return await social_listening_service.patch_query(db, ctx.site_id, query_id, body)


@router.delete("/social-listening/queries/{query_id}")
async def delete_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await social_listening_service.delete_query(db, ctx.site_id, query_id))


@router.post("/social-listening/runs", status_code=201)
async def create_run(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await social_listening_service.create_run(db, ctx.user_id, ctx.site_id)


@router.get("/social-listening/runs")
async def list_runs(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[RunResponse]:
    return await social_listening_service.list_runs(db, ctx.site_id, paging)


@router.get("/social-listening/runs/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await social_listening_service.get_run(db, ctx.site_id, run_id)


@router.patch("/social-listening/runs/{run_id}")
async def patch_run(
    run_id: str,
    body: RunUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await social_listening_service.patch_run(db, ctx.site_id, run_id, body)


@router.post("/social-listening/runs/{run_id}/collect")
async def start_collect(
    run_id: str,
    body: CollectRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await social_listening_service.start_collect(
        db, ctx.user_id, ctx.site_id, run_id, body.platform
    )


@router.post("/social-listening/posts/gate")
async def gate_posts(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> GateResponse:
    return await social_listening_service.gate_posts(db, ctx.site_id)


@router.post("/social-listening/posts/judged")
async def judge_posts(
    body: PostsJudgeRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> JudgeResponse:
    return await social_listening_service.judge_posts(db, ctx.site_id, body)


@router.get("/social-listening/posts")
async def list_posts(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    query_id: str | None = Query(None, alias="queryId"),
    run_id: str | None = Query(None, alias="runId"),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[PostResponse]:
    filters = PostFilters(
        statuses=[s for s in (status or "").split(",") if s] or None,
        platform=platform,
        query_id=query_id,
        run_id=run_id,
        q=q,
    )
    return await social_listening_service.list_posts(db, ctx.site_id, filters, paging)


@router.get("/social-listening/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SummaryResponse:
    return await social_listening_service.summary(db, ctx.site_id)


@router.get("/social-listening/posts/{post_id}")
async def get_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PostResponse:
    return await social_listening_service.get_post(db, ctx.site_id, post_id)


@router.patch("/social-listening/posts/{post_id}")
async def patch_post(
    post_id: str,
    body: PostPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PostResponse:
    return await social_listening_service.patch_post(db, ctx.site_id, post_id, body)
