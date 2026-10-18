from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.providers.social_search.models.search_cursor import SocialSearchCursor
from src.providers.social_search.models.social_post import SocialPost
from src.providers.social_search.schemas import PostEmbeddingInput


class SocialPostRepository:
    ID_PREFIX = "sp"

    async def insert_new(self, db: AsyncSession, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        now = datetime.now(UTC)
        stmt = (
            pg_insert(SocialPost)
            .values(
                [
                    {
                        "id": uid(self.ID_PREFIX),
                        "created_at": now,
                        "updated_at": now,
                        "fetched_at": now,
                        **values,
                    }
                    for values in rows
                ]
            )
            .on_conflict_do_nothing(index_elements=["post_key"])
        )
        await db.execute(stmt)
        await db.flush()

    async def ids_by_keys(self, db: AsyncSession, keys: list[str]) -> list[str]:
        if not keys:
            return []
        result = await db.execute(select(SocialPost.id).where(SocialPost.post_key.in_(keys)))
        return list(result.scalars().all())

    async def get_many(self, db: AsyncSession, post_ids: list[str]) -> list[SocialPost]:
        if not post_ids:
            return []
        result = await db.execute(select(SocialPost).where(SocialPost.id.in_(post_ids)))
        return list(result.scalars().all())

    async def by_author(
        self, db: AsyncSession, platform: str, handle: str, posted_after: datetime, limit: int
    ) -> list[SocialPost]:
        result = await db.execute(
            select(SocialPost)
            .where(
                SocialPost.platform == platform,
                func.lower(SocialPost.author_handle) == handle.lower(),
                func.coalesce(SocialPost.posted_at, SocialPost.fetched_at) > posted_after,
            )
            .order_by(SocialPost.posted_at.desc().nulls_last())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_ids(
        self,
        db: AsyncSession,
        platform: str,
        phrase: str,
        fetched_after: datetime,
        posted_after: datetime,
        limit: int,
    ) -> list[str]:
        result = await db.execute(
            select(SocialPost.id)
            .where(
                SocialPost.platform == platform,
                SocialPost.fetched_at > fetched_after,
                func.coalesce(SocialPost.posted_at, SocialPost.fetched_at) >= posted_after,
                SocialPost.search.op("@@")(func.phraseto_tsquery("english", phrase)),
            )
            .order_by(SocialPost.posted_at.desc().nulls_last())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def claim_pending_embeddings(
        self, db: AsyncSession, max_attempts: int, limit: int
    ) -> list[PostEmbeddingInput]:
        result = await db.execute(
            select(SocialPost.id, SocialPost.title, SocialPost.text)
            .where(
                SocialPost.embedding.is_(None),
                SocialPost.embed_attempts < max_attempts,
            )
            .order_by(SocialPost.seq.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return [
            PostEmbeddingInput(id=pid, title=title, text=body) for pid, title, body in result.all()
        ]

    async def write_embedding(
        self, db: AsyncSession, post_id: str, vector: list[float], model: str
    ) -> None:
        await db.execute(
            update(SocialPost)
            .where(SocialPost.id == post_id, SocialPost.embedding.is_(None))
            .values(
                embedding=vector,
                embed_model=model,
                embed_error=None,
                updated_at=datetime.now(UTC),
            )
        )

    async def mark_embed_failed(self, db: AsyncSession, post_id: str, message: str) -> None:
        await db.execute(
            update(SocialPost)
            .where(SocialPost.id == post_id)
            .values(
                embed_attempts=SocialPost.embed_attempts + 1,
                embed_error=message[:500],
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def delete_older_than(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(
            delete(SocialPost).where(
                func.coalesce(SocialPost.posted_at, SocialPost.fetched_at) < cutoff
            )
        )
        await db.flush()
        return int(result.rowcount or 0)


class SocialSearchCursorRepository:
    ID_PREFIX = "ssc"

    async def by_keyword(
        self, db: AsyncSession, platform: str, keywords: list[str]
    ) -> dict[str, datetime]:
        if not keywords:
            return {}
        result = await db.execute(
            select(SocialSearchCursor.keyword, SocialSearchCursor.last_fetched_at).where(
                SocialSearchCursor.platform == platform,
                SocialSearchCursor.keyword.in_(keywords),
            )
        )
        return dict(result.all())

    async def advance(
        self, db: AsyncSession, platform: str, keywords: list[str], fetched_at: datetime
    ) -> None:
        if not keywords:
            return
        now = datetime.now(UTC)
        stmt = pg_insert(SocialSearchCursor).values(
            [
                {
                    "id": uid(self.ID_PREFIX),
                    "platform": platform,
                    "keyword": keyword,
                    "last_fetched_at": fetched_at,
                    "created_at": now,
                    "updated_at": now,
                }
                for keyword in keywords
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="social_search_cursor_platform_keyword_key",
            set_={"last_fetched_at": stmt.excluded.last_fetched_at, "updated_at": now},
        )
        await db.execute(stmt)
        await db.flush()

    async def delete_older_than(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(
            delete(SocialSearchCursor).where(SocialSearchCursor.last_fetched_at < cutoff)
        )
        await db.flush()
        return int(result.rowcount or 0)


social_posts = SocialPostRepository()
social_search_cursors = SocialSearchCursorRepository()
