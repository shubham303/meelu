from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.find_leads.models.seen import LeadSeen


class LeadSeenRepository:
    ID_PREFIX = "ls"

    async def existing_keys(self, db: AsyncSession, site_id: str, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        result = await db.execute(
            select(LeadSeen.identity_key).where(
                LeadSeen.site_id == site_id, LeadSeen.identity_key.in_(keys)
            )
        )
        return set(result.scalars().all())

    async def remember(
        self, db: AsyncSession, user_id: str, site_id: str, keys: list[str], kind: str
    ) -> None:
        keys = list(dict.fromkeys(k for k in keys if k))
        if not keys:
            return
        now = datetime.now(UTC)
        stmt = pg_insert(LeadSeen).values(
            [
                {
                    "id": uid(self.ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "identity_key": key,
                    "kind": kind,
                    "seen_at": now,
                    "created_at": now,
                    "updated_at": now,
                }
                for key in keys
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="lead_seen_site_identity_key",
            set_={"kind": stmt.excluded.kind, "seen_at": now, "updated_at": now},
        )
        await db.execute(stmt)
        await db.flush()

    async def delete_kind_before(self, db: AsyncSession, kind: str, cutoff: datetime) -> int:
        result = await db.execute(
            delete(LeadSeen).where(LeadSeen.kind == kind, LeadSeen.seen_at < cutoff)
        )
        await db.flush()
        return int(result.rowcount or 0)


lead_seen = LeadSeenRepository()
