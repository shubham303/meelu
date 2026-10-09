from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_traffic.models.site_traffic_sync import SiteTrafficSync
from src.seo.site_traffic.schemas import TrafficSyncRecord

ACTIVE_STATUSES = ("queued", "running")


class SiteTrafficSyncRepository:
    ID_PREFIX = "tsync"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, trigger: str
    ) -> TrafficSyncRecord | None:
        stmt = (
            pg_insert(SiteTrafficSync)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                trigger=trigger,
                status="queued",
            )
            .on_conflict_do_nothing()
            .returning(SiteTrafficSync)
        )
        return self._record((await db.execute(stmt)).scalars().first())

    async def get(self, db: AsyncSession, site_id: str, id: str) -> TrafficSyncRecord | None:
        result = await db.execute(
            select(SiteTrafficSync)
            .where(SiteTrafficSync.site_id == site_id, SiteTrafficSync.id == id)
            .limit(1)
        )
        return self._record(result.scalars().first())

    async def list_recent(
        self, db: AsyncSession, site_id: str, limit: int | None = None, offset: int | None = None
    ) -> list[TrafficSyncRecord]:
        result = await db.execute(
            select(SiteTrafficSync)
            .where(SiteTrafficSync.site_id == site_id)
            .order_by(SiteTrafficSync.seq.desc())
            .limit(min(max(limit if limit is not None else 20, 1), 100))
            .offset(max(offset if offset is not None else 0, 0))
        )
        return [TrafficSyncRecord.model_validate(r) for r in result.scalars().all()]

    async def active(self, db: AsyncSession, site_id: str) -> TrafficSyncRecord | None:
        result = await db.execute(
            select(SiteTrafficSync)
            .where(
                SiteTrafficSync.site_id == site_id,
                SiteTrafficSync.status.in_(ACTIVE_STATUSES),
            )
            .limit(1)
        )
        return self._record(result.scalars().first())

    async def update(
        self, db: AsyncSession, site_id: str, id: str, patch: dict[str, Any]
    ) -> TrafficSyncRecord | None:
        values = dict(patch)
        for key in ("first_day", "last_day"):
            if isinstance(values.get(key), str):
                values[key] = date.fromisoformat(values[key])
        values["updated_at"] = datetime.now(UTC)
        stmt = (
            update(SiteTrafficSync)
            .where(SiteTrafficSync.site_id == site_id, SiteTrafficSync.id == id)
            .values(**values)
            .returning(SiteTrafficSync)
        )
        return self._record((await db.execute(stmt)).scalars().first())

    async def list_stale(self, db: AsyncSession, stale_ms: int) -> list[TrafficSyncRecord]:
        cutoff = datetime.now(UTC) - timedelta(milliseconds=stale_ms)
        result = await db.execute(
            select(SiteTrafficSync).where(
                SiteTrafficSync.status.in_(ACTIVE_STATUSES),
                text("coalesce(heartbeat_at, created_at) < :cutoff").bindparams(cutoff=cutoff),
            )
        )
        return [TrafficSyncRecord.model_validate(r) for r in result.scalars().all()]

    def _record(self, row: SiteTrafficSync | None) -> TrafficSyncRecord | None:
        return None if row is None else TrafficSyncRecord.model_validate(row)


site_traffic_syncs = SiteTrafficSyncRepository()
