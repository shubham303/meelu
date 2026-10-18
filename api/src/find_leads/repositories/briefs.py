from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.find_leads.models.brief import LeadBrief


class LeadBriefRepository:
    ID_PREFIX = "lb"

    async def get(self, db: AsyncSession, site_id: str, brief_id: str) -> LeadBrief | None:
        result = await db.execute(
            select(LeadBrief).where(LeadBrief.site_id == site_id, LeadBrief.id == brief_id).limit(1)
        )
        return result.scalars().first()

    async def get_by_text(self, db: AsyncSession, site_id: str, text: str) -> LeadBrief | None:
        result = await db.execute(
            select(LeadBrief).where(LeadBrief.site_id == site_id, LeadBrief.text == text).limit(1)
        )
        return result.scalars().first()

    async def list_enabled(self, db: AsyncSession, site_id: str) -> list[LeadBrief]:
        result = await db.execute(
            select(LeadBrief)
            .where(LeadBrief.site_id == site_id, LeadBrief.enabled.is_(True))
            .order_by(LeadBrief.seq.asc())
        )
        return list(result.scalars().all())

    async def count(self, db: AsyncSession, site_id: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(LeadBrief).where(LeadBrief.site_id == site_id)
        )
        return int(result.scalar_one())

    async def existing_texts(self, db: AsyncSession, site_id: str, texts: list[str]) -> set[str]:
        if not texts:
            return set()
        result = await db.execute(
            select(LeadBrief.text).where(LeadBrief.site_id == site_id, LeadBrief.text.in_(texts))
        )
        return set(result.scalars().all())

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> LeadBrief:
        now = datetime.now(UTC)
        row = LeadBrief(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            plan={},
            created_at=now,
            updated_at=now,
            **values,
        )
        db.add(row)
        await db.flush()
        return row

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[dict[str, Any]]
    ) -> None:
        now = datetime.now(UTC)
        for item in items:
            stmt = pg_insert(LeadBrief).values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                plan={},
                created_at=now,
                updated_at=now,
                **item,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="lead_brief_site_text_key",
                set_={
                    "enabled": stmt.excluded.enabled,
                    "sources": stmt.excluded.sources,
                    "updated_at": now,
                },
            )
            await db.execute(stmt)
        await db.flush()

    async def update(self, db: AsyncSession, row: LeadBrief, values: dict[str, Any]) -> LeadBrief:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def delete(self, db: AsyncSession, row: LeadBrief) -> None:
        await db.delete(row)
        await db.flush()

    async def list(self, db: AsyncSession, site_id: str) -> list[LeadBrief]:
        result = await db.execute(
            select(LeadBrief).where(LeadBrief.site_id == site_id).order_by(LeadBrief.seq.asc())
        )
        return list(result.scalars().all())


lead_briefs = LeadBriefRepository()
