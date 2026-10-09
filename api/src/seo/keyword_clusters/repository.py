from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, literal_column, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.seo.keyword_clusters.constants import CLUSTER_ID_PREFIX
from src.seo.keyword_clusters.models.seo_keyword_cluster import SeoKeywordCluster
from src.seo.keyword_clusters.schemas import (
    ClusterDraft,
    ClusterFilters,
    ClusterMetrics,
    ClusterRecord,
)

KEY = ("site_id", "location_code", "language_code", "main_keyword")

MERGED = {
    column: literal_column(
        f"ARRAY(SELECT DISTINCT k FROM unnest(seo_keyword_clusters.{column} || excluded.{column}) AS k)"
    )
    for column in ("keywords", "seeds")
}

RANKED = (
    SeoKeywordCluster.winnability.desc().nulls_last(),
    SeoKeywordCluster.volume.desc(),
    SeoKeywordCluster.main_keyword,
)


class KeywordClusterRepository:
    async def get(self, db: AsyncSession, site_id: str, cluster_id: str) -> ClusterRecord | None:
        row = await db.scalar(
            select(SeoKeywordCluster).where(
                SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id == cluster_id
            )
        )
        return None if row is None else ClusterRecord.model_validate(row)

    async def list(
        self, db: AsyncSession, site_id: str, filters: ClusterFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[ClusterRecord]:
        query = select(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id)
        if filters.search:
            like = f"%{filters.search.strip().lower()}%"
            query = query.where(
                or_(
                    SeoKeywordCluster.main_keyword.like(like),
                    func.array_to_string(SeoKeywordCluster.keywords, " ").like(like),
                )
            )
        if filters.min_volume is not None:
            query = query.where(SeoKeywordCluster.volume >= filters.min_volume)
        if filters.scored is True:
            query = query.where(SeoKeywordCluster.metrics_at.is_not(None))
        if filters.scored is False:
            query = query.where(SeoKeywordCluster.metrics_at.is_(None))
        if filters.ranked is not None:
            query = query.where(SeoKeywordCluster.is_ranked.is_(filters.ranked))
        return await PaginationService.paginate_query(
            db, query.order_by(*RANKED), paging.page, paging.page_size, ClusterRecord
        )

    async def clustered_keywords(
        self, db: AsyncSession, site_id: str, location_code: int, language_code: str
    ) -> set[str]:
        rows = await db.scalars(
            select(func.unnest(SeoKeywordCluster.keywords)).where(
                SeoKeywordCluster.site_id == site_id,
                SeoKeywordCluster.location_code == location_code,
                SeoKeywordCluster.language_code == language_code,
            )
        )
        return set(rows)

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, drafts: list[ClusterDraft]
    ) -> list[ClusterRecord]:
        if not drafts:
            return []
        now = datetime.now(UTC)
        values = [
            {
                **d.model_dump(),
                "id": uid(CLUSTER_ID_PREFIX),
                "user_id": user_id,
                "site_id": site_id,
                "created_at": now,
                "updated_at": now,
            }
            for d in drafts
        ]
        statement = insert(SeoKeywordCluster).values(values)
        rows = await db.scalars(
            statement.on_conflict_do_update(
                index_elements=list(KEY),
                set_={
                    **MERGED,
                    "volume": statement.excluded.volume,
                    "core_keyword": statement.excluded.core_keyword,
                    "updated_at": now,
                },
            )
            .returning(SeoKeywordCluster)
            .execution_options(populate_existing=True)
        )
        return [ClusterRecord.model_validate(r) for r in rows]

    async def needing_metrics(
        self,
        db: AsyncSession,
        site_id: str,
        cluster_ids: list[str] | None,
        stale_before: datetime,
        limit: int,
    ) -> list[ClusterRecord]:
        query = select(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id)
        if cluster_ids:
            query = query.where(SeoKeywordCluster.id.in_(cluster_ids))
        else:
            query = query.where(
                or_(
                    SeoKeywordCluster.metrics_at.is_(None),
                    SeoKeywordCluster.metrics_at < stale_before,
                )
            )
        rows = await db.scalars(
            query.order_by(SeoKeywordCluster.volume.desc(), SeoKeywordCluster.main_keyword).limit(
                limit
            )
        )
        return [ClusterRecord.model_validate(r) for r in rows]

    async def mark_ranked(self, db: AsyncSession, site_id: str, cluster_ids: list[str]) -> None:
        if not cluster_ids:
            return
        await db.execute(
            update(SeoKeywordCluster)
            .where(SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id.in_(cluster_ids))
            .values(is_ranked=True, updated_at=datetime.now(UTC))
        )

    async def set_metrics(
        self, db: AsyncSession, site_id: str, cluster_id: str, metrics: ClusterMetrics
    ) -> ClusterRecord:
        now = datetime.now(UTC)
        ranked = {"is_ranked": True} if metrics.our_position is not None else {}
        row = await db.scalar(
            update(SeoKeywordCluster)
            .where(SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id == cluster_id)
            .values(**metrics.model_dump(), **ranked, metrics_at=now, updated_at=now)
            .returning(SeoKeywordCluster)
            .execution_options(populate_existing=True)
        )
        return ClusterRecord.model_validate(row)

    async def delete(self, db: AsyncSession, site_id: str, cluster_id: str) -> bool:
        result = await db.execute(
            delete(SeoKeywordCluster).where(
                SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id == cluster_id
            )
        )
        return bool(result.rowcount)


seo_keyword_clusters = KeywordClusterRepository()
