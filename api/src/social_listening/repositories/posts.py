from datetime import UTC, datetime
from typing import Any

from sqlalchemy import REAL, case, cast, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.social_listening.models.post import SocialListeningPost
from src.social_listening.schemas import PostEmbeddingInput, PostFilters, PostResponse


class SocialListeningPostRepository:
    ID_PREFIX = "slp"

    async def get(self, db: AsyncSession, site_id: str, post_id: str) -> SocialListeningPost | None:
        result = await db.execute(
            select(SocialListeningPost)
            .where(SocialListeningPost.site_id == site_id, SocialListeningPost.id == post_id)
            .limit(1)
        )
        return result.scalars().first()

    async def get_many(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> dict[str, SocialListeningPost]:
        if not ids:
            return {}
        result = await db.execute(
            select(SocialListeningPost).where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.id.in_(ids)
            )
        )
        return {row.id: row for row in result.scalars().all()}

    async def existing_keys(self, db: AsyncSession, site_id: str, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        result = await db.execute(
            select(SocialListeningPost.post_key).where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.post_key.in_(keys)
            )
        )
        return set(result.scalars().all())

    async def existing_hashes(
        self, db: AsyncSession, site_id: str, hashes: list[str]
    ) -> set[str]:
        if not hashes:
            return set()
        result = await db.execute(
            select(SocialListeningPost.content_hash).where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.content_hash.in_(hashes),
            )
        )
        return set(result.scalars().all())

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[dict[str, Any]]
    ) -> int:
        if not rows:
            return 0
        now = datetime.now(UTC)
        stmt = (
            pg_insert(SocialListeningPost)
            .values(
                [
                    {
                        "id": uid(self.ID_PREFIX),
                        "user_id": user_id,
                        "site_id": site_id,
                        "created_at": now,
                        "updated_at": now,
                        **values,
                    }
                    for values in rows
                ]
            )
            .on_conflict_do_nothing(constraint="social_listening_post_site_key_key")
            .returning(SocialListeningPost.id)
        )
        result = await db.execute(stmt)
        await db.flush()
        return len(result.all())

    async def update(
        self, db: AsyncSession, row: SocialListeningPost, values: dict[str, Any]
    ) -> PostResponse:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return PostResponse.model_validate(row)

    async def list_all(
        self, db: AsyncSession, site_id: str, filters: PostFilters
    ) -> list[SocialListeningPost]:
        result = await db.execute(
            select(SocialListeningPost)
            .where(*self._conditions(site_id, filters))
            .order_by(*self._order(filters.sort))
        )
        return list(result.scalars().all())

    async def status_counts(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        result = await db.execute(
            select(SocialListeningPost.status, func.count())
            .where(SocialListeningPost.site_id == site_id)
            .group_by(SocialListeningPost.status)
        )
        return dict(result.all())

    async def counts_by_query(
        self, db: AsyncSession, site_id: str, statuses: tuple[str, ...] | None = None
    ) -> dict[str, int]:
        conds = [SocialListeningPost.site_id == site_id, SocialListeningPost.query_id.is_not(None)]
        if statuses is not None:
            conds.append(SocialListeningPost.status.in_(statuses))
        result = await db.execute(
            select(SocialListeningPost.query_id, func.count())
            .where(*conds)
            .group_by(SocialListeningPost.query_id)
        )
        return {qid: int(n) for qid, n in result.all()}

    async def count_pending_gate(
        self,
        db: AsyncSession,
        site_id: str,
        embeddable_query_ids: list[str],
        unembedded_query_ids: list[str],
    ) -> int:
        if not embeddable_query_ids:
            return 0
        result = await db.execute(
            select(func.count()).where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "fetched",
                SocialListeningPost.embed_attempts < 3,
                SocialListeningPost.query_id.in_(embeddable_query_ids),
                or_(
                    SocialListeningPost.embedding.is_(None),
                    SocialListeningPost.query_id.in_(unembedded_query_ids),
                ),
            )
        )
        return int(result.scalar_one())

    async def apply_similarity(
        self,
        db: AsyncSession,
        site_id: str,
        query_vectors: dict[str, list[float]],
        min_similarity: float,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for query_id, vector in query_vectors.items():
            similarity = 1 - SocialListeningPost.embedding.cosine_distance(vector)
            kept = similarity >= min_similarity
            result = await db.execute(
                update(SocialListeningPost)
                .where(
                    SocialListeningPost.site_id == site_id,
                    SocialListeningPost.status == "fetched",
                    SocialListeningPost.query_id == query_id,
                    SocialListeningPost.embedding.is_not(None),
                )
                .values(
                    similarity=similarity,
                    status=case((kept, "matched"), else_="dropped"),
                    drop_reason=case((kept, None), else_="far_in_meaning"),
                    updated_at=func.now(),
                )
                .returning(SocialListeningPost.status)
            )
            for (status,) in result.all():
                counts[status] = counts.get(status, 0) + 1
        await db.flush()
        return counts

    async def drop_orphaned(
        self, db: AsyncSession, site_id: str, live_query_ids: list[str]
    ) -> int:
        result = await db.execute(
            update(SocialListeningPost)
            .where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "fetched",
                or_(
                    SocialListeningPost.query_id.is_(None),
                    SocialListeningPost.query_id.not_in(live_query_ids),
                ),
            )
            .values(status="dropped", drop_reason="line_removed", updated_at=func.now())
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def drop_unembeddable(
        self, db: AsyncSession, site_id: str, failed_query_ids: list[str], max_attempts: int
    ) -> int:
        result = await db.execute(
            update(SocialListeningPost)
            .where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "fetched",
                or_(
                    SocialListeningPost.embed_attempts >= max_attempts,
                    SocialListeningPost.query_id.in_(failed_query_ids),
                ),
            )
            .values(status="dropped", drop_reason="unembeddable", updated_at=func.now())
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def list_pending_embeddings(
        self, db: AsyncSession, max_attempts: int, limit: int
    ) -> list[PostEmbeddingInput]:
        result = await db.execute(
            select(SocialListeningPost.id, SocialListeningPost.title, SocialListeningPost.text)
            .where(
                SocialListeningPost.embedding.is_(None),
                SocialListeningPost.status == "fetched",
                SocialListeningPost.embed_attempts < max_attempts,
                SocialListeningPost.query_id.is_not(None),
                func.coalesce(SocialListeningPost.title, SocialListeningPost.text).is_not(None),
            )
            .order_by(SocialListeningPost.embed_attempts.asc(), SocialListeningPost.seq.asc())
            .limit(limit)
        )
        return [
            PostEmbeddingInput(id=pid, title=title, text=body) for pid, title, body in result.all()
        ]

    async def write_embedding(
        self, db: AsyncSession, post_id: str, vector: list[float], model: str
    ) -> None:
        await db.execute(
            update(SocialListeningPost)
            .where(SocialListeningPost.id == post_id, SocialListeningPost.embedding.is_(None))
            .values(
                embedding=vector,
                embed_model=model,
                embed_error=None,
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def mark_embed_failed(self, db: AsyncSession, post_id: str, message: str) -> None:
        await db.execute(
            update(SocialListeningPost)
            .where(SocialListeningPost.id == post_id)
            .values(
                embed_attempts=SocialListeningPost.embed_attempts + 1,
                embed_error=message[:500],
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def list(
        self, db: AsyncSession, site_id: str, filters: PostFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[PostResponse]:
        query = (
            select(SocialListeningPost)
            .where(*self._conditions(site_id, filters))
            .order_by(*self._order(filters.sort))
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, PostResponse
        )

    def _order(self, sort: str | None) -> Any:
        if sort == "newest":
            return (
                SocialListeningPost.posted_at.desc().nulls_last(),
                SocialListeningPost.seq.desc(),
            )
        if sort == "engaged":
            return (
                func.coalesce(
                    cast(SocialListeningPost.engagement["score"].astext, REAL), 0.0
                ).desc(),
                SocialListeningPost.seq.desc(),
            )
        if sort == "similarity":
            return (
                SocialListeningPost.similarity.desc().nulls_last(),
                SocialListeningPost.seq.asc(),
            )
        return (
            SocialListeningPost.composite_score.desc().nulls_last(),
            SocialListeningPost.seq.desc(),
        )

    def _conditions(self, site_id: str, f: PostFilters) -> Any:
        conds = [SocialListeningPost.site_id == site_id]
        if f.statuses:
            conds.append(SocialListeningPost.status.in_(f.statuses))
        if f.platform:
            conds.append(SocialListeningPost.platform == f.platform)
        if f.query_id:
            conds.append(SocialListeningPost.query_id == f.query_id)
        if f.run_id:
            conds.append(SocialListeningPost.run_id == f.run_id)
        if f.min_relevance is not None:
            conds.append(SocialListeningPost.relevance >= f.min_relevance)
        if f.q:
            like = f"%{f.q}%"
            conds.append(
                or_(
                    func.coalesce(SocialListeningPost.title, "").ilike(like),
                    func.coalesce(SocialListeningPost.text, "").ilike(like),
                )
            )
        return conds


social_listening_posts = SocialListeningPostRepository()
