from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.clusters.repository import seo_keyword_clusters
from src.seo.clusters.schemas import ClusterRecord


class SeoKeywordClusterService:
    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[ClusterRecord]:
        return await seo_keyword_clusters.list(db, site_id, paging)


seo_keyword_cluster_service = SeoKeywordClusterService()
