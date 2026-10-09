from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.keyword_clusters.models.seo_keyword_cluster_competitor import (
    SeoKeywordClusterCompetitor,
)
from src.seo.site_seo.models.seo_competitor import SeoCompetitor


class ClusterCompetitorRepository:
    async def link(self, db: AsyncSession, links: list[tuple[str, str]]) -> None:
        if not links:
            return
        statement = insert(SeoKeywordClusterCompetitor).values(
            [{"cluster_id": c, "competitor_id": k} for c, k in dict.fromkeys(links)]
        )
        await db.execute(statement.on_conflict_do_nothing())

    async def domains_by_cluster(
        self, db: AsyncSession, cluster_ids: list[str]
    ) -> dict[str, list[str]]:
        if not cluster_ids:
            return {}
        rows = await db.execute(
            select(SeoKeywordClusterCompetitor.cluster_id, SeoCompetitor.domain)
            .join(SeoCompetitor, SeoCompetitor.id == SeoKeywordClusterCompetitor.competitor_id)
            .where(SeoKeywordClusterCompetitor.cluster_id.in_(cluster_ids))
            .order_by(SeoCompetitor.domain)
        )
        found: dict[str, list[str]] = {}
        for cluster_id, domain in rows.all():
            found.setdefault(cluster_id, []).append(domain)
        return found


seo_cluster_competitors = ClusterCompetitorRepository()
