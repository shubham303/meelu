from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.social_listening.models.query import SocialListeningQuery
from src.social_listening.schemas import QueryEmbeddingInput


class SocialListeningQueryRepository:
    ID_PREFIX = "slq"

    async def get(
        self, db: AsyncSession, site_id: str, query_id: str
    ) -> SocialListeningQuery | None:
        result = await db.execute(
            select(SocialListeningQuery)
            .where(SocialListeningQuery.site_id == site_id, SocialListeningQuery.id == query_id)
            .limit(1)
        )
        return result.scalars().first()

    async def existing_ids(self, db: AsyncSession, site_id: str, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        result = await db.execute(
            select(SocialListeningQuery.id).where(
                SocialListeningQuery.site_id == site_id,
                SocialListeningQuery.id.in_(ids),
            )
        )
        return set(result.scalars().all())

    async def existing_texts(self, db: AsyncSession, site_id: str, texts: list[str]) -> set[str]:
        if not texts:
            return set()
        result = await db.execute(
            select(SocialListeningQuery.text).where(
                SocialListeningQuery.site_id == site_id,
                SocialListeningQuery.text.in_(texts),
            )
        )
        return set(result.scalars().all())

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[dict[str, Any]]
    ) -> None:
        now = datetime.now(UTC)
        for item in items:
            stmt = pg_insert(SocialListeningQuery).values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                created_at=now,
                updated_at=now,
                **item,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="social_listening_query_site_text_key",
                set_={
                    "enabled": stmt.excluded.enabled,
                    "source": stmt.excluded.source,
                    "updated_at": now,
                },
            )
            await db.execute(stmt)
        await db.flush()

    async def update(
        self, db: AsyncSession, row: SocialListeningQuery, values: dict[str, Any]
    ) -> SocialListeningQuery:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def delete(self, db: AsyncSession, row: SocialListeningQuery) -> None:
        await db.delete(row)
        await db.flush()

    async def embedding_states(self, db: AsyncSession, site_id: str) -> dict[str, tuple[bool, int]]:
        result = await db.execute(
            select(
                SocialListeningQuery.id,
                SocialListeningQuery.embedding.is_not(None),
                SocialListeningQuery.embed_attempts,
            ).where(SocialListeningQuery.site_id == site_id)
        )
        return {qid: (bool(has), int(attempts)) for qid, has, attempts in result.all()}

    async def embeddings_by_ids(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> dict[str, list[float]]:
        if not ids:
            return {}
        result = await db.execute(
            select(SocialListeningQuery.id, SocialListeningQuery.embedding).where(
                SocialListeningQuery.site_id == site_id,
                SocialListeningQuery.id.in_(ids),
                SocialListeningQuery.embedding.is_not(None),
            )
        )
        return {qid: [float(x) for x in vector] for qid, vector in result.all()}

    async def list_pending_embeddings(
        self, db: AsyncSession, max_attempts: int, limit: int
    ) -> list[QueryEmbeddingInput]:
        result = await db.execute(
            select(SocialListeningQuery.id, SocialListeningQuery.text)
            .where(
                SocialListeningQuery.embedding.is_(None),
                SocialListeningQuery.embed_attempts < max_attempts,
            )
            .order_by(SocialListeningQuery.embed_attempts.asc(), SocialListeningQuery.seq.asc())
            .limit(limit)
        )
        return [QueryEmbeddingInput(id=qid, text=text) for qid, text in result.all()]

    async def write_embedding(
        self, db: AsyncSession, query_id: str, vector: list[float], model: str
    ) -> None:
        await db.execute(
            update(SocialListeningQuery)
            .where(SocialListeningQuery.id == query_id, SocialListeningQuery.embedding.is_(None))
            .values(
                embedding=vector,
                embed_model=model,
                embed_error=None,
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def mark_embed_failed(self, db: AsyncSession, query_id: str, message: str) -> None:
        await db.execute(
            update(SocialListeningQuery)
            .where(SocialListeningQuery.id == query_id)
            .values(
                embed_attempts=SocialListeningQuery.embed_attempts + 1,
                embed_error=message[:500],
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def list(self, db: AsyncSession, site_id: str) -> list[SocialListeningQuery]:
        result = await db.execute(
            select(SocialListeningQuery)
            .where(SocialListeningQuery.site_id == site_id)
            .order_by(SocialListeningQuery.seq.asc())
        )
        return list(result.scalars().all())


social_listening_queries = SocialListeningQueryRepository()
