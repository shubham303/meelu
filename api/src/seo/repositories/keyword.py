from datetime import datetime
from typing import Any

from sqlalchemy import Select, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.models.keyword import SeoKeyword
from src.seo.repositories.base import count, now, page, vector_list
from src.seo.schemas import KeywordFilter, KeywordRecord, KeywordVector

TOP_QUERIES_SQL = """
select keyword from seo_keywords
where site_id = :site_id and not branded and impressions_28d > 0
order by impressions_28d desc limit :limit
"""

STALE_FACTS_SQL = """
select keyword from seo_keywords
where site_id = :site_id and id = any(cast(:ids as text[]))
  and (facts_fetched_at is null or facts_fetched_at < :cutoff)
order by keyword
"""

APPLY_FACTS_SQL = """
update seo_keywords set volume = :volume, difficulty = :difficulty, cpc = :cpc, intent = :intent,
  facts_fetched_at = :at, updated_at = :at
where site_id = :site_id and keyword = :keyword
"""

APPLY_RANKED_SQL = """
update seo_keywords set our_position = :position, our_url = :url,
  volume = coalesce(volume, :volume), difficulty = coalesce(difficulty, :difficulty),
  cpc = coalesce(cpc, :cpc), intent = coalesce(intent, :intent),
  facts_fetched_at = coalesce(facts_fetched_at, :at), updated_at = :at
where site_id = :site_id and keyword = :keyword
"""

SEARCH_COUNTS_SQL = """
update seo_keywords set
  impressions_28d = :impressions_28d, clicks_28d = :clicks_28d,
  impressions_prev_28d = :impressions_prev_28d, clicks_prev_28d = :clicks_prev_28d,
  impressions_ly_28d = :impressions_ly_28d, clicks_ly_28d = :clicks_ly_28d,
  updated_at = now()
where site_id = :site_id and keyword = :keyword
"""

BRANDED_SQL = """
update seo_keywords k set branded = exists (
  select 1 from unnest(cast(:terms as text[])) t where k.keyword like '%' || t || '%'
), updated_at = now()
where k.site_id = :site_id
"""

SET_EMBEDDING_SQL = """
update seo_keywords set embedding = cast(:embedding as vector), embed_model = :model,
  updated_at = now()
where id = :id
"""

CLUSTERABLE_SQL = """
select id, keyword, volume, difficulty, impressions_28d, embedding::text as embedding
from seo_keywords
where site_id = :site_id and embedding is not null and not branded
  and (coalesce(volume, 0) > 0 or impressions_28d > 0)
order by coalesce(volume, 0) desc, impressions_28d desc
limit :limit
"""

UNCLUSTERED_SQL = """
select id, embedding::text as embedding from seo_keywords
where site_id = :site_id and embedding is not null and cluster_id is null
"""

class SeoKeywordRepository:
    ID_PREFIX = "kw"
    INSERT_CHUNK = 1000

    def _filtered(self, site_id: str, f: KeywordFilter) -> Select:
        query = select(SeoKeyword).where(SeoKeyword.site_id == site_id)
        if f.source:
            query = query.where(SeoKeyword.first_source == f.source)
        if f.cluster_id:
            query = query.where(SeoKeyword.cluster_id == f.cluster_id)
        if f.branded is not None:
            query = query.where(SeoKeyword.branded == f.branded)
        if f.has_facts is not None:
            query = query.where(
                SeoKeyword.facts_fetched_at.is_not(None)
                if f.has_facts
                else SeoKeyword.facts_fetched_at.is_(None)
            )
        if f.search:
            query = query.where(SeoKeyword.keyword.ilike(f"%{f.search}%"))
        return query

    async def get(self, db: AsyncSession, site_id: str, keyword_id: str) -> KeywordRecord | None:
        row = (
            await db.execute(
                select(SeoKeyword).where(SeoKeyword.site_id == site_id, SeoKeyword.id == keyword_id)
            )
        ).scalar_one_or_none()
        return None if row is None else KeywordRecord.model_validate(row)

    async def find(self, db: AsyncSession, site_id: str, keyword: str) -> KeywordRecord | None:
        row = (
            await db.execute(
                select(SeoKeyword).where(
                    SeoKeyword.site_id == site_id, SeoKeyword.keyword == keyword
                )
            )
        ).scalar_one_or_none()
        return None if row is None else KeywordRecord.model_validate(row)

    async def list_by_ids(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> list[KeywordRecord]:
        if not keyword_ids:
            return []
        rows = (
            await db.execute(
                select(SeoKeyword).where(
                    SeoKeyword.site_id == site_id, SeoKeyword.id.in_(keyword_ids)
                )
            )
        ).scalars()
        return [KeywordRecord.model_validate(r) for r in rows]

    async def ids_for(self, db: AsyncSession, site_id: str, keywords: list[str]) -> dict[str, str]:
        if not keywords:
            return {}
        rows = await db.execute(
            select(SeoKeyword.keyword, SeoKeyword.id).where(
                SeoKeyword.site_id == site_id, SeoKeyword.keyword.in_(keywords)
            )
        )
        return {k: i for k, i in rows.tuples()}

    async def seeded_terms(
        self, db: AsyncSession, site_id: str, seed_keyword_id: str, source: str
    ) -> list[str]:
        rows = await db.execute(
            select(SeoKeyword.keyword).where(
                SeoKeyword.site_id == site_id,
                SeoKeyword.seed_keyword_id == seed_keyword_id,
                SeoKeyword.first_source == source,
            )
        )
        return list(rows.scalars().all())

    async def count(self, db: AsyncSession, site_id: str, with_facts: bool = False) -> int:
        query = select(SeoKeyword).where(SeoKeyword.site_id == site_id)
        if with_facts:
            query = query.where(SeoKeyword.facts_fetched_at.is_not(None))
        return await count(db, query)

    async def insert_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        keywords: list[str],
        source: str,
        seed_keyword_id: str | None = None,
    ) -> list[str]:
        if not keywords:
            return []
        at = now()
        inserted: list[str] = []
        unique = list(dict.fromkeys(keywords))
        for start in range(0, len(unique), self.INSERT_CHUNK):
            stmt = (
                insert(SeoKeyword)
                .values(
                    [
                        {
                            "id": uid(self.ID_PREFIX),
                            "user_id": user_id,
                            "site_id": site_id,
                            "keyword": k,
                            "first_source": source,
                            "seed_keyword_id": seed_keyword_id,
                            "created_at": at,
                            "updated_at": at,
                        }
                        for k in unique[start : start + self.INSERT_CHUNK]
                    ]
                )
                .on_conflict_do_nothing(index_elements=["site_id", "keyword"])
                .returning(SeoKeyword.id)
            )
            inserted += list((await db.execute(stmt)).scalars().all())
        return inserted

    async def top_query_terms(self, db: AsyncSession, site_id: str, limit: int) -> list[str]:
        rows = await db.execute(text(TOP_QUERIES_SQL), {"site_id": site_id, "limit": limit})
        return [r[0] for r in rows]

    async def stale_terms(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str], cutoff: datetime
    ) -> list[str]:
        rows = await db.execute(
            text(STALE_FACTS_SQL), {"site_id": site_id, "ids": keyword_ids, "cutoff": cutoff}
        )
        return [r[0] for r in rows]

    async def apply_facts(self, db: AsyncSession, rows: list[dict[str, Any]]) -> None:
        if rows:
            await db.execute(text(APPLY_FACTS_SQL), rows)

    async def apply_ranked(self, db: AsyncSession, rows: list[dict[str, Any]]) -> None:
        if rows:
            await db.execute(text(APPLY_RANKED_SQL), rows)

    async def apply_search_counts(
        self, db: AsyncSession, site_id: str, rows: list[dict[str, Any]]
    ) -> None:
        if rows:
            await db.execute(text(SEARCH_COUNTS_SQL), [{**r, "site_id": site_id} for r in rows])

    async def mark_branded(self, db: AsyncSession, site_id: str, terms: list[str]) -> None:
        await db.execute(text(BRANDED_SQL), {"site_id": site_id, "terms": terms})

    async def pending_embedding(
        self, db: AsyncSession, site_id: str, limit: int
    ) -> list[tuple[str, str]]:
        rows = await db.execute(
            select(SeoKeyword.id, SeoKeyword.keyword)
            .where(
                SeoKeyword.site_id == site_id,
                SeoKeyword.embedding.is_(None),
                SeoKeyword.embed_error.is_(None),
            )
            .order_by(SeoKeyword.seq)
            .limit(limit)
        )
        return [(i, k) for i, k in rows.tuples()]

    async def set_embeddings(self, db: AsyncSession, rows: list[dict[str, str]]) -> None:
        if rows:
            await db.execute(text(SET_EMBEDDING_SQL), rows)

    async def embedded_ids(self, db: AsyncSession, site_id: str) -> list[str]:
        rows = await db.execute(
            select(SeoKeyword.id).where(
                SeoKeyword.site_id == site_id, SeoKeyword.embedding.is_not(None)
            )
        )
        return list(rows.scalars().all())

    async def clusterable(self, db: AsyncSession, site_id: str, limit: int) -> list[dict[str, Any]]:
        rows = await db.execute(text(CLUSTERABLE_SQL), {"site_id": site_id, "limit": limit})
        return [dict(r) for r in rows.mappings()]

    async def unclustered_embedded(self, db: AsyncSession, site_id: str) -> list[dict[str, Any]]:
        rows = await db.execute(text(UNCLUSTERED_SQL), {"site_id": site_id})
        return [dict(r) for r in rows.mappings()]

    async def assign_cluster(
        self, db: AsyncSession, cluster_id: str, keyword_ids: list[str]
    ) -> None:
        if keyword_ids:
            await db.execute(
                update(SeoKeyword)
                .where(SeoKeyword.id.in_(keyword_ids))
                .values(cluster_id=cluster_id)
            )

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[KeywordRecord]:
        rows = (
            await db.execute(
                select(SeoKeyword)
                .where(SeoKeyword.site_id == site_id)
                .order_by(SeoKeyword.impressions_28d.desc(), SeoKeyword.volume.desc().nulls_last())
            )
        ).scalars()
        return [KeywordRecord.model_validate(r) for r in rows]

    async def list_by_cluster_ids(
        self, db: AsyncSession, site_id: str, cluster_ids: list[str]
    ) -> list[KeywordRecord]:
        if not cluster_ids:
            return []
        rows = (
            await db.execute(
                select(SeoKeyword)
                .where(SeoKeyword.site_id == site_id, SeoKeyword.cluster_id.in_(set(cluster_ids)))
                .order_by(SeoKeyword.seq)
            )
        ).scalars()
        return [KeywordRecord.model_validate(r) for r in rows]

    async def list_for_topic(
        self, db: AsyncSession, site_id: str, topic_id: str
    ) -> list[KeywordRecord]:
        rows = (
            await db.execute(
                select(SeoKeyword)
                .where(
                    SeoKeyword.site_id == site_id,
                    (SeoKeyword.id == topic_id) | (SeoKeyword.seed_keyword_id == topic_id),
                    SeoKeyword.branded.is_(False),
                )
                .order_by(SeoKeyword.seq)
            )
        ).scalars()
        return [KeywordRecord.model_validate(r) for r in rows]

    async def branded_ids(self, db: AsyncSession, site_id: str) -> set[str]:
        rows = await db.execute(
            select(SeoKeyword.id).where(SeoKeyword.site_id == site_id, SeoKeyword.branded)
        )
        return set(rows.scalars().all())

    async def embeddings_by_ids(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> dict[str, list[float]]:
        if not keyword_ids:
            return {}
        rows = await db.execute(
            select(SeoKeyword.id, SeoKeyword.embedding).where(
                SeoKeyword.site_id == site_id,
                SeoKeyword.id.in_(set(keyword_ids)),
                SeoKeyword.embedding.is_not(None),
            )
        )
        return {i: vector_list(e) for i, e in rows.tuples()}

    async def list_embedded(self, db: AsyncSession, site_id: str) -> list[KeywordVector]:
        rows = await db.execute(
            select(SeoKeyword.id, SeoKeyword.keyword, SeoKeyword.embedding)
            .where(SeoKeyword.site_id == site_id, SeoKeyword.embedding.is_not(None))
            .order_by(SeoKeyword.seq)
        )
        return [
            KeywordVector(id=i, keyword=k, embedding=vector_list(e)) for i, k, e in rows.tuples()
        ]

    async def set_cluster_if_unset(
        self, db: AsyncSession, keyword_id: str, cluster_id: str
    ) -> None:
        await db.execute(
            update(SeoKeyword)
            .where(SeoKeyword.id == keyword_id, SeoKeyword.cluster_id.is_(None))
            .values(cluster_id=cluster_id, updated_at=now())
        )

    async def list(
        self, db: AsyncSession, site_id: str, f: KeywordFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[KeywordRecord]:
        return await page(
            db,
            self._filtered(site_id, f),
            (
                SeoKeyword.impressions_28d.desc(),
                SeoKeyword.volume.desc().nulls_last(),
                SeoKeyword.seq,
            ),
            paging,
            KeywordRecord,
        )


seo_keywords = SeoKeywordRepository()
