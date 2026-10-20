from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.geo.schemas import (
    CheckResponse,
    ChecksStartRequest,
    ChecksStartResponse,
    ChecksStopResponse,
    DeleteResponse,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    SummaryResponse,
    UpsertResponse,
)
from src.geo.service import geo_service

router = APIRouter()


@router.get("/geo/queries")
async def list_queries(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[QueryResponse]:
    return await geo_service.list_queries(db, ctx.site_id)


@router.post("/geo/queries")
async def upsert_queries(
    body: list[QueryUpsertItem],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> UpsertResponse:
    return await geo_service.upsert_queries(db, ctx.user_id, ctx.site_id, body)


@router.get("/geo/queries/{query_id}")
async def get_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> QueryResponse:
    return await geo_service.get_query(db, ctx.site_id, query_id)


@router.patch("/geo/queries/{query_id}")
async def patch_query(
    query_id: str,
    body: QueryPatchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> QueryResponse:
    return await geo_service.patch_query(db, ctx.site_id, query_id, body)


@router.delete("/geo/queries/{query_id}")
async def delete_query(
    query_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await geo_service.delete_query(db, ctx.site_id, query_id))


@router.get("/geo/queries/{query_id}/checks")
async def list_checks(
    query_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[CheckResponse]:
    return await geo_service.list_checks(db, ctx.site_id, query_id, paging)


@router.post("/geo/checks")
async def start_checks(
    body: ChecksStartRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ChecksStartResponse:
    return await geo_service.start_checks(db, ctx.user_id, ctx.site_id, body.query_ids)


@router.post("/geo/checks/stop")
async def stop_checks(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ChecksStopResponse:
    return await geo_service.stop_checks(db, ctx.site_id)


@router.get("/geo/checks/{check_id}")
async def get_check(
    check_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CheckResponse:
    return await geo_service.get_check(db, ctx.site_id, check_id)


@router.delete("/geo/checks/{check_id}")
async def delete_check(
    check_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> DeleteResponse:
    return DeleteResponse(id=await geo_service.delete_check(db, ctx.site_id, check_id))


@router.get("/geo/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SummaryResponse:
    return await geo_service.summary(db, ctx.site_id)
