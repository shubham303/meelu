from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import ARRAY, Text, cast, delete, func, literal_column, or_, select, update
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

    async def get_many(
        self, db: AsyncSession, site_id: str, cluster_ids: list[str]
    ) -> list[ClusterRecord]:
        if not cluster_ids:
            return []
        rows = await db.scalars(
            select(SeoKeywordCluster).where(
                SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id.in_(cluster_ids)
            )
        )
        return [ClusterRecord.model_validate(r) for r in rows]

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

    async def containing(
        self, db: AsyncSession, site_id: str, keyword: str, location_code: int, language_code: str
    ) -> ClusterRecord | None:
        row = await db.scalar(
            select(SeoKeywordCluster)
            .where(
                SeoKeywordCluster.site_id == site_id,
                SeoKeywordCluster.location_code == location_code,
                SeoKeywordCluster.language_code == language_code,
                SeoKeywordCluster.keywords.any(keyword),
            )
            .order_by(SeoKeywordCluster.volume.desc())
            .limit(1)
        )
        return None if row is None else ClusterRecord.model_validate(row)

    async def containing_any(
        self,
        db: AsyncSession,
        site_id: str,
        keywords: list[str],
        location_code: int,
        language_code: str,
    ) -> list[ClusterRecord]:
        rows = await db.scalars(
            select(SeoKeywordCluster)
            .where(
                SeoKeywordCluster.site_id == site_id,
                SeoKeywordCluster.location_code == location_code,
                SeoKeywordCluster.language_code == language_code,
                SeoKeywordCluster.keywords.op("&&")(cast(keywords, ARRAY(Text))),
            )
            .order_by(SeoKeywordCluster.volume.desc(), SeoKeywordCluster.main_keyword)
        )
        return [ClusterRecord.model_validate(r) for r in rows]

    async def labelled_mains(
        self,
        db: AsyncSession,
        site_id: str,
        location_code: int,
        language_code: str,
        main_keywords: list[str],
    ) -> set[str]:
        rows = await db.scalars(
            select(SeoKeywordCluster.main_keyword).where(
                SeoKeywordCluster.site_id == site_id,
                SeoKeywordCluster.location_code == location_code,
                SeoKeywordCluster.language_code == language_code,
                SeoKeywordCluster.main_keyword.in_(main_keywords),
                SeoKeywordCluster.intent.is_not(None),
                SeoKeywordCluster.importance.is_not(None),
                SeoKeywordCluster.is_brand_keyword.is_not(None),
            )
        )
        return set(rows)

    async def with_cores(
        self,
        db: AsyncSession,
        site_id: str,
        location_code: int,
        language_code: str,
        cores: list[str],
    ) -> list[ClusterRecord]:
        if not cores:
            return []
        rows = await db.scalars(
            select(SeoKeywordCluster)
            .where(
                SeoKeywordCluster.site_id == site_id,
                SeoKeywordCluster.location_code == location_code,
                SeoKeywordCluster.language_code == language_code,
                SeoKeywordCluster.core_keyword.in_(cores),
            )
            .order_by(SeoKeywordCluster.volume.desc(), SeoKeywordCluster.main_keyword)
        )
        return [ClusterRecord.model_validate(r) for r in rows]

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
                    "intent": func.coalesce(SeoKeywordCluster.intent, statement.excluded.intent),
                    "importance": func.coalesce(
                        SeoKeywordCluster.importance, statement.excluded.importance
                    ),
                    "is_brand_keyword": func.coalesce(
                        SeoKeywordCluster.is_brand_keyword, statement.excluded.is_brand_keyword
                    ),
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
        self,
        db: AsyncSession,
        site_id: str,
        cluster_id: str,
        metrics: ClusterMetrics,
        competitors: list[str],
    ) -> ClusterRecord:
        now = datetime.now(UTC)
        ranked = {"is_ranked": True} if metrics.our_position is not None else {}
        row = await db.scalar(
            update(SeoKeywordCluster)
            .where(SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id == cluster_id)
            .values(
                **metrics.model_dump(),
                **ranked,
                competitors=competitors,
                metrics_at=now,
                updated_at=now,
            )
            .returning(SeoKeywordCluster)
            .execution_options(populate_existing=True)
        )
        return ClusterRecord.model_validate(row)

    async def clear_metrics(
        self, db: AsyncSession, site_id: str, cluster_id: str, serp_verdict: str
    ) -> ClusterRecord:
        now = datetime.now(UTC)
        row = await db.scalar(
            update(SeoKeywordCluster)
            .where(SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id == cluster_id)
            .values(
                winnability=None,
                p_top_three=None,
                p_page_one=None,
                likely_position=None,
                our_position=None,
                our_url=None,
                our_strength=None,
                intent_fit=None,
                serp_verdict=serp_verdict,
                climb=[],
                competitors=[],
                metrics_at=now,
                updated_at=now,
            )
            .returning(SeoKeywordCluster)
            .execution_options(populate_existing=True)
        )
        return ClusterRecord.model_validate(row)

    async def set_members(
        self,
        db: AsyncSession,
        site_id: str,
        cluster_id: str,
        keywords: list[str],
        volume: int,
        is_ranked: bool,
    ) -> ClusterRecord:
        row = await db.scalar(
            update(SeoKeywordCluster)
            .where(SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id == cluster_id)
            .values(
                keywords=keywords,
                volume=volume,
                is_ranked=is_ranked,
                updated_at=datetime.now(UTC),
            )
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

    async def delete_many(self, db: AsyncSession, site_id: str, cluster_ids: list[str]) -> None:
        if not cluster_ids:
            return
        await db.execute(
            delete(SeoKeywordCluster).where(
                SeoKeywordCluster.site_id == site_id, SeoKeywordCluster.id.in_(cluster_ids)
            )
        )


seo_keyword_clusters = KeywordClusterRepository()
