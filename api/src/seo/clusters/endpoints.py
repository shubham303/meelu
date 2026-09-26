from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.seo.clusters.schemas import ClusterRecord
from src.seo.clusters.service import seo_keyword_cluster_service

router = APIRouter()


@router.get("/clusters")
async def list_clusters(
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[ClusterRecord]:
    return await seo_keyword_cluster_service.list(db, ctx.site_id, paging)
