from datetime import UTC, datetime
from typing import Any

from sqlalchemy import bindparam, delete, func, literal, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.providers.social_search.models.social_post import SocialPost
from src.social_listening.models.post import SocialListeningPost
from src.social_listening.schemas import PostFilters, PostResponse

POST_FIELDS = (
    "url",
    "platform",
    "external_id",
    "title",
    "text",
    "author_handle",
    "author_name",
    "posted_at",
    "engagement",
    "context",
)

FRESH_CANDIDATES = text(
    """
    SELECT DISTINCT ON (coalesce(sp.content_hash, sp.id)) sp.id
      FROM social_post sp
     WHERE sp.id IN :post_ids
       AND NOT EXISTS (
           SELECT 1 FROM social_listening_post own
            WHERE own.site_id = :site_id AND own.post_id = sp.id)
       AND (sp.content_hash IS NULL OR NOT EXISTS (
           SELECT 1 FROM social_listening_post own
             JOIN social_post seen ON seen.id = own.post_id
            WHERE own.site_id = :site_id AND seen.content_hash = sp.content_hash))
     ORDER BY coalesce(sp.content_hash, sp.id), sp.posted_at DESC NULLS LAST
    """
).bindparams(bindparam("post_ids", expanding=True))

MATCH_CANDIDATES = text(
    """
    WITH scored AS (
        SELECT DISTINCT ON (own.id)
               own.id, q.id AS query_id, 1 - (sp.embedding <=> q.embedding) AS similarity
          FROM social_listening_post own
          JOIN social_post sp ON sp.id = own.post_id
          JOIN social_listening_query q
            ON q.site_id = own.site_id AND q.enabled AND q.embedding IS NOT NULL
         WHERE own.site_id = :site_id
           AND own.status = 'candidate'
           AND sp.embedding IS NOT NULL
         ORDER BY own.id, sp.embedding <=> q.embedding
    )
    UPDATE social_listening_post own
       SET status = 'matched', query_id = scored.query_id,
           similarity = scored.similarity, updated_at = now()
      FROM scored
     WHERE own.id = scored.id AND scored.similarity >= :min_similarity
    """
)


class SocialListeningPostRepository:
    ID_PREFIX = "slp"

    def _joined(self):
        return select(SocialListeningPost, SocialPost).join(
            SocialPost, SocialPost.id == SocialListeningPost.post_id
        )

    def _response(self, own: SocialListeningPost, post: SocialPost) -> PostResponse:
        return PostResponse(
            id=own.id,
            site_id=own.site_id,
            post_id=own.post_id,
            status=own.status,
            similarity=own.similarity,
            keep_reason=own.keep_reason,
            suggested_angle=own.suggested_angle,
            reply_text=own.reply_text,
            replied_at=own.replied_at,
            query_id=own.query_id,
            run_id=own.run_id,
            created_at=own.created_at,
            updated_at=own.updated_at,
            **{field: getattr(post, field) for field in POST_FIELDS},
        )

    async def get(self, db: AsyncSession, site_id: str, post_id: str) -> SocialListeningPost | None:
        result = await db.execute(
            select(SocialListeningPost)
            .where(SocialListeningPost.site_id == site_id, SocialListeningPost.id == post_id)
            .limit(1)
        )
        return result.scalars().first()

    async def get_response(
        self, db: AsyncSession, site_id: str, post_id: str
    ) -> PostResponse | None:
        result = await db.execute(
            self._joined()
            .where(SocialListeningPost.site_id == site_id, SocialListeningPost.id == post_id)
            .limit(1)
        )
        row = result.first()
        return None if row is None else self._response(*row)

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

    async def get_many_with_posts(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> list[tuple[SocialListeningPost, SocialPost]]:
        if not ids:
            return []
        result = await db.execute(
            self._joined().where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.id.in_(ids)
            )
        )
        return [(own, post) for own, post in result.all()]

    async def insert_candidates(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, post_ids: list[str]
    ) -> int:
        if not post_ids:
            return 0
        fresh = (
            (await db.execute(FRESH_CANDIDATES, {"site_id": site_id, "post_ids": post_ids}))
            .scalars()
            .all()
        )
        if not fresh:
            return 0
        now = datetime.now(UTC)
        result = await db.execute(
            pg_insert(SocialListeningPost)
            .values(
                [
                    {
                        "id": uid(self.ID_PREFIX),
                        "user_id": user_id,
                        "site_id": site_id,
                        "post_id": post_id,
                        "run_id": run_id,
                        "status": "candidate",
                        "created_at": now,
                        "updated_at": now,
                    }
                    for post_id in fresh
                ]
            )
            .on_conflict_do_nothing(constraint="social_listening_post_site_post_key")
            .returning(SocialListeningPost.id)
        )
        await db.flush()
        return len(result.all())

    async def count_unembedded_candidates(
        self, db: AsyncSession, site_id: str, max_attempts: int
    ) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(SocialListeningPost)
            .join(SocialPost, SocialPost.id == SocialListeningPost.post_id)
            .where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "candidate",
                SocialPost.embedding.is_(None),
                SocialPost.embed_attempts < max_attempts,
            )
        )
        return int(result.scalar_one())

    async def delete_unembeddable_candidates(
        self, db: AsyncSession, site_id: str, max_attempts: int
    ) -> int:
        failed = select(SocialPost.id).where(
            SocialPost.embedding.is_(None), SocialPost.embed_attempts >= max_attempts
        )
        result = await db.execute(
            delete(SocialListeningPost).where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "candidate",
                SocialListeningPost.post_id.in_(failed),
            )
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def match_candidates(self, db: AsyncSession, site_id: str, min_similarity: float) -> int:
        result = await db.execute(
            MATCH_CANDIDATES, {"site_id": site_id, "min_similarity": min_similarity}
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def delete_embedded_candidates(self, db: AsyncSession, site_id: str) -> int:
        embedded = select(SocialPost.id).where(SocialPost.embedding.is_not(None))
        result = await db.execute(
            delete(SocialListeningPost).where(
                SocialListeningPost.site_id == site_id,
                SocialListeningPost.status == "candidate",
                SocialListeningPost.post_id.in_(embedded),
            )
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def delete_many(self, db: AsyncSession, site_id: str, ids: list[str]) -> int:
        if not ids:
            return 0
        result = await db.execute(
            delete(SocialListeningPost).where(
                SocialListeningPost.site_id == site_id, SocialListeningPost.id.in_(ids)
            )
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def update(
        self, db: AsyncSession, row: SocialListeningPost, values: dict[str, Any]
    ) -> SocialListeningPost:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

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

    async def list(
        self, db: AsyncSession, site_id: str, filters: PostFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[PostResponse]:
        params = PaginationParams(page=paging.page, page_size=paging.page_size).validate()
        conds = self._conditions(site_id, filters)
        total = (
            await db.execute(
                select(func.count())
                .select_from(SocialListeningPost)
                .join(SocialPost, SocialPost.id == SocialListeningPost.post_id)
                .where(*conds)
            )
        ).scalar_one()
        result = await db.execute(
            self._joined()
            .where(*conds)
            .order_by(SocialPost.posted_at.desc().nulls_last(), SocialListeningPost.seq.desc())
            .offset(params.offset)
            .limit(params.page_size)
        )
        return PaginatedApiResponse(
            data=[self._response(own, post) for own, post in result.all()],
            pagination=PaginationService.build_pagination_meta(
                int(total), params.page, params.page_size
            ),
        )

    def _conditions(self, site_id: str, f: PostFilters) -> Any:
        conds: list[Any] = [SocialListeningPost.site_id == site_id]
        if f.statuses:
            conds.append(SocialListeningPost.status.in_(f.statuses))
        if f.platform:
            conds.append(SocialPost.platform == f.platform)
        if f.query_id:
            conds.append(SocialListeningPost.query_id == f.query_id)
        if f.run_id:
            conds.append(SocialListeningPost.run_id == f.run_id)
        if f.q:
            like = f"%{f.q}%"
            conds.append(
                or_(
                    func.coalesce(SocialPost.title, literal("")).ilike(like),
                    func.coalesce(SocialPost.text, literal("")).ilike(like),
                )
            )
        return conds


social_listening_posts = SocialListeningPostRepository()
