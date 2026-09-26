from datetime import UTC, datetime
from typing import Any

from sqlalchemy import REAL, case, cast, func, or_, select, update
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

    async def find_by_urls(
        self, db: AsyncSession, site_id: str, urls: list[str]
    ) -> dict[str, SocialListeningPost]:
        if not urls:
            return {}
        result = await db.execute(
            select(SocialListeningPost).where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.url.in_(urls)
            )
        )
        return {row.url: row for row in result.scalars().all()}

    async def known_urls(self, db: AsyncSession, site_id: str, urls: list[str]) -> list[str]:
        if not urls:
            return []
        result = await db.execute(
            select(SocialListeningPost.url).where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.url.in_(urls)
            )
        )
        return [u for (u,) in result.all()]

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[dict[str, Any]]
    ) -> int:
        if not rows:
            return 0
        now = datetime.now(UTC)
        db.add_all(
            [
                SocialListeningPost(
                    id=uid(self.ID_PREFIX),
                    user_id=user_id,
                    site_id=site_id,
                    created_at=now,
                    updated_at=now,
                    **values,
                )
                for values in rows
            ]
        )
        await db.flush()
        return len(rows)

    async def update(
        self, db: AsyncSession, row: SocialListeningPost, values: dict[str, Any]
    ) -> PostResponse:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return PostResponse.model_validate(row)

    async def delete(self, db: AsyncSession, row: SocialListeningPost) -> None:
        await db.delete(row)
        await db.flush()

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

    async def kind_counts(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        result = await db.execute(
            select(SocialListeningPost.kind, func.count())
            .where(SocialListeningPost.site_id == site_id)
            .group_by(SocialListeningPost.kind)
        )
        return dict(result.all())

    async def class_counts(
        self, db: AsyncSession, site_id: str, classes: tuple[str, ...]
    ) -> dict[str, int]:
        cols = [func.count().filter(SocialListeningPost.classes.contains([cls])) for cls in classes]
        result = await db.execute(select(*cols).where(SocialListeningPost.site_id == site_id))
        return dict(zip(classes, result.one()))

    async def sentiment_counts(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        result = await db.execute(
            select(SocialListeningPost.sentiment, func.count())
            .where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.sentiment.is_not(None)
            )
            .group_by(SocialListeningPost.sentiment)
        )
        return dict(result.all())

    async def counts_by_query(
        self, db: AsyncSession, site_id: str, statuses: tuple[str, ...]
    ) -> dict[str, int]:
        result = await db.execute(
            select(SocialListeningPost.query_id, func.count())
            .where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.query_id.is_not(None),
                SocialListeningPost.status.in_(statuses),
            )
            .group_by(SocialListeningPost.query_id)
        )
        return {qid: int(n) for qid, n in result.all()}

    async def match_target_posts(self, db: AsyncSession, site_id: str) -> int:
        result = await db.execute(
            update(SocialListeningPost)
            .where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "fetched",
                SocialListeningPost.query_id.is_(None),
            )
            .values(status="matched", updated_at=func.now())
        )
        await db.flush()
        return int(result.rowcount or 0)

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
                    status=case((kept, "matched"), else_="filtered"),
                    keep_reason=case((kept, None), else_="Too far from the query"),
                    updated_at=func.now(),
                )
                .returning(SocialListeningPost.status)
            )
            for (status,) in result.all():
                counts[status] = counts.get(status, 0) + 1
        await db.flush()
        return counts

    async def filter_unembeddable(
        self,
        db: AsyncSession,
        site_id: str,
        live_query_ids: list[str],
        failed_query_ids: list[str],
    ) -> int:
        result = await db.execute(
            update(SocialListeningPost)
            .where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "fetched",
                SocialListeningPost.query_id.is_not(None),
                or_(
                    SocialListeningPost.embed_attempts >= 3,
                    SocialListeningPost.query_id.in_(failed_query_ids),
                    SocialListeningPost.query_id.not_in(live_query_ids),
                ),
            )
            .values(status="filtered", keep_reason="Could not be embedded", updated_at=func.now())
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
        if f.kind:
            conds.append(SocialListeningPost.kind == f.kind)
        if f.status:
            conds.append(SocialListeningPost.status == f.status)
        if f.platform:
            conds.append(SocialListeningPost.platform == f.platform)
        if f.intent:
            conds.append(SocialListeningPost.intent == f.intent)
        if f.sentiment:
            conds.append(SocialListeningPost.sentiment == f.sentiment)
        if f.cls:
            conds.append(SocialListeningPost.classes.contains([f.cls]))
        if f.target:
            conds.append(SocialListeningPost.matched_targets.contains([f.target]))
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
