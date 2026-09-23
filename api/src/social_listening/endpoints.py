from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.social_listening import service
from src.social_listening.schemas import (
    BulkUpsertResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    DeleteResponse,
    GateResponse,
    KnownUrlsRequest,
    PostFilters,
    PostPatchRequest,
    PostResponse,
    PostsBulkRequest,
    PostsClassifyRequest,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    RunResponse,
    RunUpdateRequest,
    SummaryResponse,
    TargetPatchRequest,
    TargetResponse,
    TargetUpsertItem,
)

router = APIRouter()


@router.get("/social-listening/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConfigResponse:
    return await service.get_config(db, ctx.user_id, ctx.site_id)


@router.put("/social-listening/config")
async def put_config(
    body: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConfigResponse:
    return await service.update_config(db, ctx.user_id, ctx.site_id, body)


@router.get("/social-listening/queries")
async def list_queries(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[QueryResponse]:
    return await service.list_queries(db, ctx.site_id)


@router.post("/social-listening/queries")
async def upsert_queries(
    body: list[QueryUpsertItem],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BulkUpsertResponse:
    return await service.upsert_queries(db, ctx.user_id, ctx.site_id, body)


@router.patch("/social-listening/queries/{query_id}")
async def patch_query(
    query_id: str,
    body: QueryPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> QueryResponse:
    return await service.patch_query(db, ctx.site_id, query_id, body)


@router.delete("/social-listening/queries/{query_id}")
async def delete_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await service.delete_query(db, ctx.site_id, query_id))


@router.get("/social-listening/targets")
async def list_targets(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[TargetResponse]:
    return await service.list_targets(db, ctx.site_id)


@router.post("/social-listening/targets")
async def upsert_targets(
    body: list[TargetUpsertItem],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BulkUpsertResponse:
    return await service.upsert_targets(db, ctx.user_id, ctx.site_id, body)


@router.patch("/social-listening/targets/{target_id}")
async def patch_target(
    target_id: str,
    body: TargetPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
):
    return await service.patch_target(db, ctx.site_id, target_id, body)


@router.delete("/social-listening/targets/{target_id}")
async def delete_target(
    target_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await service.delete_target(db, ctx.site_id, target_id))


@router.post("/social-listening/runs", status_code=201)
async def create_run(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await service.create_run(db, ctx.user_id, ctx.site_id)


@router.get("/social-listening/runs")
async def list_runs(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[RunResponse]:
    return await service.list_runs(db, ctx.site_id, paging)


@router.get("/social-listening/runs/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await service.get_run(db, ctx.site_id, run_id)


@router.patch("/social-listening/runs/{run_id}")
async def patch_run(
    run_id: str,
    body: RunUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> RunResponse:
    return await service.patch_run(db, ctx.site_id, run_id, body)


@router.post("/social-listening/posts/known")
async def known_post_urls(
    body: KnownUrlsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[str]:
    return await service.known_urls(db, ctx.site_id, body.urls)


@router.post("/social-listening/posts/bulk")
async def bulk_upsert_posts(
    body: PostsBulkRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BulkUpsertResponse:
    return await service.bulk_upsert_posts(db, ctx.user_id, ctx.site_id, body)


@router.post("/social-listening/posts/gate")
async def gate_posts(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> GateResponse:
    return await service.gate_posts(db, ctx.user_id, ctx.site_id)


@router.post("/social-listening/posts/classified")
async def classify_posts(
    body: PostsClassifyRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> BulkUpsertResponse:
    return await service.classify_posts(db, ctx.site_id, body)


@router.get("/social-listening/posts")
async def list_posts(
    kind: str | None = Query(None),
    status: str | None = Query(None),
    platform: str | None = Query(None),
    intent: str | None = Query(None),
    sentiment: str | None = Query(None),
    cls: str | None = Query(None),
    target: str | None = Query(None),
    query_id: str | None = Query(None, alias="queryId"),
    run_id: str | None = Query(None, alias="runId"),
    min_relevance: float | None = Query(None, alias="minRelevance"),
    q: str | None = Query(None),
    sort: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[PostResponse]:
    filters = PostFilters(
        kind=kind,
        status=status,
        platform=platform,
        intent=intent,
        sentiment=sentiment,
        cls=cls,
        target=target,
        query_id=query_id,
        run_id=run_id,
        min_relevance=min_relevance,
        q=q,
        sort=sort,
    )
    return await service.list_posts(db, ctx.site_id, filters, paging)


@router.get("/social-listening/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SummaryResponse:
    return await service.summary(db, ctx.site_id)


@router.get("/social-listening/posts/{post_id}")
async def get_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PostResponse:
    return await service.get_post(db, ctx.site_id, post_id)


@router.patch("/social-listening/posts/{post_id}")
async def patch_post(
    post_id: str,
    body: PostPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PostResponse:
    return await service.patch_post(db, ctx.site_id, post_id, body)


@router.delete("/social-listening/posts/{post_id}")
async def delete_post(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await service.delete_post(db, ctx.site_id, post_id))
