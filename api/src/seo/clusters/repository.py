from datetime import datetime

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.clusters.model import SeoKeywordCluster
from src.seo.clusters.schemas import ClusterRecord
from src.seo.common.repository import count, page

SIMILARITY_CUTOFF_SQL = """
select percentile_cont(:pct / 100.0) within group (order by site_similarity)
from seo_keyword_clusters where site_id = :site_id and site_similarity is not null
"""

INSERT_SQL = """
insert into seo_keyword_clusters (id, user_id, site_id, head_keyword_id, centroid, size, volume_sum,
  difficulty_median, site_similarity, rebuilt_at, created_at, updated_at)
values (:id, :user_id, :site_id, :head, cast(:centroid as vector), :size, :volume,
  :difficulty, :similarity, :now, :now, :now)
"""


class SeoKeywordClusterRepository:
    ID_PREFIX = "cl"

    async def find_by_head(
        self, db: AsyncSession, site_id: str, head_keyword_id: str
    ) -> ClusterRecord | None:
        row = (
            await db.execute(
                select(SeoKeywordCluster).where(
                    SeoKeywordCluster.site_id == site_id,
                    SeoKeywordCluster.head_keyword_id == head_keyword_id,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else ClusterRecord.model_validate(row)

    async def count(self, db: AsyncSession, site_id: str) -> int:
        return await count(
            db, select(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id)
        )

    async def similarity_cutoff(self, db: AsyncSession, site_id: str, pct: float) -> float | None:
        return (
            await db.execute(text(SIMILARITY_CUTOFF_SQL), {"site_id": site_id, "pct": pct})
        ).scalar()

    async def delete_for_site(self, db: AsyncSession, site_id: str) -> None:
        await db.execute(delete(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id))

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        head_keyword_id: str,
        centroid: str,
        size: int,
        volume_sum: int,
        difficulty_median: float | None,
        site_similarity: float | None,
        at: datetime,
    ) -> str:
        cluster_id = uid(self.ID_PREFIX)
        await db.execute(
            text(INSERT_SQL),
            {
                "id": cluster_id,
                "user_id": user_id,
                "site_id": site_id,
                "head": head_keyword_id,
                "centroid": centroid,
                "size": size,
                "volume": volume_sum,
                "difficulty": difficulty_median,
                "similarity": site_similarity,
                "now": at,
            },
        )
        return cluster_id

    async def set_owner(
        self, db: AsyncSession, cluster_id: str, page_id: str, coverage: float
    ) -> None:
        await db.execute(
            update(SeoKeywordCluster)
            .where(SeoKeywordCluster.id == cluster_id)
            .values(owner_page_id=page_id, owner_coverage=coverage)
        )

    async def list_by_ids(
        self, db: AsyncSession, site_id: str, cluster_ids: list[str]
    ) -> list[ClusterRecord]:
        if not cluster_ids:
            return []
        rows = (
            await db.execute(
                select(SeoKeywordCluster).where(
                    SeoKeywordCluster.site_id == site_id,
                    SeoKeywordCluster.id.in_(set(cluster_ids)),
                )
            )
        ).scalars()
        return [ClusterRecord.model_validate(r) for r in rows]

    async def list_owned(self, db: AsyncSession, site_id: str) -> list[ClusterRecord]:
        rows = (
            await db.execute(
                select(SeoKeywordCluster)
                .where(
                    SeoKeywordCluster.site_id == site_id,
                    SeoKeywordCluster.owner_page_id.is_not(None),
                )
                .order_by(SeoKeywordCluster.volume_sum.desc(), SeoKeywordCluster.seq)
            )
        ).scalars()
        return [ClusterRecord.model_validate(r) for r in rows]

    async def list_uncovered(
        self, db: AsyncSession, site_id: str, owner_coverage: float
    ) -> list[ClusterRecord]:
        rows = (
            await db.execute(
                select(SeoKeywordCluster)
                .where(
                    SeoKeywordCluster.site_id == site_id,
                    SeoKeywordCluster.owner_page_id.is_(None)
                    | (func.coalesce(SeoKeywordCluster.owner_coverage, 0) < owner_coverage),
                )
                .order_by(SeoKeywordCluster.seq)
            )
        ).scalars()
        return [ClusterRecord.model_validate(r) for r in rows]

    async def neighbour_ids(
        self, db: AsyncSession, site_id: str, cluster_ids: list[str], distance: float
    ) -> dict[str, set[str]]:
        if not cluster_ids:
            return {}
        near = aliased(SeoKeywordCluster)
        rows = await db.execute(
            select(SeoKeywordCluster.id, near.id).where(
                SeoKeywordCluster.site_id == site_id,
                SeoKeywordCluster.id.in_(set(cluster_ids)),
                near.site_id == site_id,
                near.id != SeoKeywordCluster.id,
                near.centroid.is_not(None),
                near.centroid.cosine_distance(SeoKeywordCluster.centroid) <= distance,
            )
        )
        found: dict[str, set[str]] = {i: set() for i in cluster_ids}
        for cluster_id, neighbour_id in rows.tuples():
            found[cluster_id].add(neighbour_id)
        return found

    async def nearest_id(
        self, db: AsyncSession, site_id: str, vector: list[float], distance: float
    ) -> str | None:
        gap = SeoKeywordCluster.centroid.cosine_distance(vector)
        return (
            await db.execute(
                select(SeoKeywordCluster.id)
                .where(
                    SeoKeywordCluster.site_id == site_id,
                    SeoKeywordCluster.centroid.is_not(None),
                    gap <= distance,
                )
                .order_by(gap)
                .limit(1)
            )
        ).scalar_one_or_none()

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[ClusterRecord]:
        query = select(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id)
        return await page(db, query, SeoKeywordCluster.volume_sum.desc(), paging, ClusterRecord)


seo_keyword_clusters = SeoKeywordClusterRepository()
