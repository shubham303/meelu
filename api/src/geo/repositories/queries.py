from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.geo.models.query import GeoQuery


class GeoQueryRepository:
    ID_PREFIX = "geq"

    async def get(self, db: AsyncSession, site_id: str, query_id: str) -> GeoQuery | None:
        result = await db.execute(
            select(GeoQuery).where(GeoQuery.site_id == site_id, GeoQuery.id == query_id).limit(1)
        )
        return result.scalars().first()

    async def get_by_text(self, db: AsyncSession, site_id: str, text: str) -> GeoQuery | None:
        result = await db.execute(
            select(GeoQuery).where(GeoQuery.site_id == site_id, GeoQuery.text == text).limit(1)
        )
        return result.scalars().first()

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[GeoQuery]:
        result = await db.execute(
            select(GeoQuery).where(GeoQuery.site_id == site_id).order_by(GeoQuery.seq.asc())
        )
        return list(result.scalars().all())

    async def list_by_ids(self, db: AsyncSession, site_id: str, ids: list[str]) -> list[GeoQuery]:
        if not ids:
            return []
        result = await db.execute(
            select(GeoQuery)
            .where(GeoQuery.site_id == site_id, GeoQuery.id.in_(set(ids)))
            .order_by(GeoQuery.seq.asc())
        )
        return list(result.scalars().all())

    async def list_enabled(self, db: AsyncSession, site_id: str) -> list[GeoQuery]:
        result = await db.execute(
            select(GeoQuery)
            .where(GeoQuery.site_id == site_id, GeoQuery.enabled.is_(True))
            .order_by(GeoQuery.seq.asc())
        )
        return list(result.scalars().all())

    async def existing_texts(self, db: AsyncSession, site_id: str, texts: list[str]) -> set[str]:
        if not texts:
            return set()
        result = await db.execute(
            select(GeoQuery.text).where(GeoQuery.site_id == site_id, GeoQuery.text.in_(texts))
        )
        return set(result.scalars().all())

    async def count(self, db: AsyncSession, site_id: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(GeoQuery).where(GeoQuery.site_id == site_id)
        )
        return int(result.scalar_one())

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[dict[str, Any]]
    ) -> None:
        now = datetime.now(UTC)
        for item in items:
            stmt = pg_insert(GeoQuery).values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                created_at=now,
                updated_at=now,
                **item,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="geo_query_site_text_key",
                set_={
                    "enabled": stmt.excluded.enabled,
                    "source": stmt.excluded.source,
                    "updated_at": now,
                },
            )
            await db.execute(stmt)
        await db.flush()

    async def update(self, db: AsyncSession, row: GeoQuery, values: dict[str, Any]) -> GeoQuery:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def delete(self, db: AsyncSession, row: GeoQuery) -> None:
        await db.delete(row)
        await db.flush()


geo_queries = GeoQueryRepository()
