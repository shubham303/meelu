from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.social_listening.models.social_post import SocialPost
from src.social_listening.schemas import PostEmbeddingInput


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

    async def search_ids(
        self, db: AsyncSession, platform: str, phrase: str, fetched_after: datetime, limit: int
    ) -> list[str]:
        result = await db.execute(
            select(SocialPost.id)
            .where(
                SocialPost.platform == platform,
                SocialPost.fetched_at > fetched_after,
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


social_posts = SocialPostRepository()
