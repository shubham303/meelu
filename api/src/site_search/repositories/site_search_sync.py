from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.site_search.models.site_search_sync import SiteSearchSync
from src.site_search.schemas import SearchSyncRecord

ACTIVE_STATUSES = ("queued", "running")


class SiteSearchSyncRepository:
    ID_PREFIX = "ssync"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, trigger: str
    ) -> SearchSyncRecord | None:
        stmt = (
            pg_insert(SiteSearchSync)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                trigger=trigger,
                status="queued",
            )
            .on_conflict_do_nothing()
            .returning(SiteSearchSync)
        )
        return self._record((await db.execute(stmt)).scalars().first())

    async def get(self, db: AsyncSession, site_id: str, id: str) -> SearchSyncRecord | None:
        result = await db.execute(
            select(SiteSearchSync)
            .where(SiteSearchSync.site_id == site_id, SiteSearchSync.id == id)
            .limit(1)
        )
        return self._record(result.scalars().first())

    async def latest(self, db: AsyncSession, site_id: str) -> SearchSyncRecord | None:
        result = await db.execute(
            select(SiteSearchSync)
            .where(SiteSearchSync.site_id == site_id)
            .order_by(SiteSearchSync.seq.desc())
            .limit(1)
        )
        return self._record(result.scalars().first())

    async def active(self, db: AsyncSession, site_id: str) -> SearchSyncRecord | None:
        result = await db.execute(
            select(SiteSearchSync)
            .where(SiteSearchSync.site_id == site_id, SiteSearchSync.status.in_(ACTIVE_STATUSES))
            .limit(1)
        )
        return self._record(result.scalars().first())

    async def update(
        self, db: AsyncSession, site_id: str, id: str, patch: dict[str, Any]
    ) -> SearchSyncRecord | None:
        values = dict(patch)
        for key in ("first_day", "last_day"):
            if isinstance(values.get(key), str):
                values[key] = date.fromisoformat(values[key])
        values["updated_at"] = datetime.now(UTC)
        stmt = (
            update(SiteSearchSync)
            .where(SiteSearchSync.site_id == site_id, SiteSearchSync.id == id)
            .values(**values)
            .returning(SiteSearchSync)
        )
        return self._record((await db.execute(stmt)).scalars().first())

    async def fail_stalled(self, db: AsyncSession, site_id: str, stale_ms: int, error: str) -> int:
        now = datetime.now(UTC)
        cutoff = now - timedelta(milliseconds=stale_ms)
        stmt = (
            update(SiteSearchSync)
            .where(
                SiteSearchSync.site_id == site_id,
                SiteSearchSync.status.in_(ACTIVE_STATUSES),
                text("coalesce(heartbeat_at, created_at) < :cutoff").bindparams(cutoff=cutoff),
            )
            .values(status="failed", error=error, finished_at=now, updated_at=now)
            .returning(SiteSearchSync.id)
        )
        return len((await db.execute(stmt)).scalars().all())

    def _record(self, row: SiteSearchSync | None) -> SearchSyncRecord | None:
        return None if row is None else SearchSyncRecord.model_validate(row)


site_search_syncs = SiteSearchSyncRepository()
