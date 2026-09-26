from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.social_listening.models.target import SocialListeningTarget
from src.social_listening.schemas import TargetResponse


class SocialListeningTargetRepository:
    ID_PREFIX = "slt"

    async def get(
        self, db: AsyncSession, site_id: str, target_id: str
    ) -> SocialListeningTarget | None:
        result = await db.execute(
            select(SocialListeningTarget)
            .where(SocialListeningTarget.site_id == site_id, SocialListeningTarget.id == target_id)
            .limit(1)
        )
        return result.scalars().first()

    async def existing_keys(
        self, db: AsyncSession, site_id: str, keys: list[tuple[str, str]]
    ) -> set[tuple[str, str]]:
        if not keys:
            return set()
        result = await db.execute(
            select(SocialListeningTarget.kind, SocialListeningTarget.name).where(
                SocialListeningTarget.site_id == site_id
            )
        )
        have = {(kind, name) for kind, name in result.all()}
        return {k for k in keys if k in have}

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[dict[str, Any]]
    ) -> None:
        now = datetime.now(UTC)
        for item in items:
            stmt = pg_insert(SocialListeningTarget).values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                created_at=now,
                updated_at=now,
                **item,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="social_listening_target_site_kind_name_key",
                set_={
                    "enabled": stmt.excluded.enabled,
                    "source": stmt.excluded.source,
                    "updated_at": now,
                },
            )
            await db.execute(stmt)
        await db.flush()

    async def update(
        self, db: AsyncSession, row: SocialListeningTarget, values: dict[str, Any]
    ) -> TargetResponse:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return TargetResponse.model_validate(row)

    async def delete(self, db: AsyncSession, row: SocialListeningTarget) -> None:
        await db.delete(row)
        await db.flush()

    async def list(self, db: AsyncSession, site_id: str) -> list[TargetResponse]:
        result = await db.execute(
            select(SocialListeningTarget)
            .where(SocialListeningTarget.site_id == site_id)
            .order_by(SocialListeningTarget.kind.asc(), SocialListeningTarget.seq.asc())
        )
        return [TargetResponse.model_validate(r) for r in result.scalars().all()]


social_listening_targets = SocialListeningTargetRepository()
