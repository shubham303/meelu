from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.providers.registry import Caller
from src.seo.keyword_clusters.schemas import (
    ClusterFilters,
    ClusterRecord,
    KeywordsClusterRequest,
)
from src.seo.keyword_clusters.service import keyword_cluster_service

router = APIRouter()


@router.get("/site/seo/clusters")
async def list_clusters(
    search: str | None = Query(None),
    min_volume: int | None = Query(None, alias="minVolume"),
    ranked: bool | None = Query(None),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[ClusterRecord]:
    filters = ClusterFilters(search=search, min_volume=min_volume, ranked=ranked)
    return await keyword_cluster_service.list(db, ctx.site_id, filters, paging)


@router.get("/site/seo/clusters/{cluster_id}")
async def get_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ClusterRecord:
    return await keyword_cluster_service.get(db, ctx.site_id, cluster_id)


@router.delete("/site/seo/clusters/{cluster_id}")
async def delete_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> Response:
    await keyword_cluster_service.delete(db, ctx.site_id, cluster_id)
    return Response(status_code=204)


@router.delete("/site/seo/clusters/{cluster_id}/keywords")
async def remove_cluster_keyword(
    cluster_id: str,
    keyword: list[str] = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ClusterRecord:
    return await keyword_cluster_service.remove_keywords(
        db,
        Caller(user_id=ctx.user_id, site_id=ctx.site_id),
        ctx.site_id,
        cluster_id,
        KeywordsClusterRequest(keywords=keyword),
    )
