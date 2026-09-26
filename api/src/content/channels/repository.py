from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models.site_channels import SiteChannel
from src.content.schemas.channels import SiteChannelRecord
from src.core.ids import uid


class SiteChannelRepository:
    ID_PREFIX = "chn"

    async def get(
        self, db: AsyncSession, site_id: str, channel_key: str
    ) -> SiteChannelRecord | None:
        row = (
            await db.execute(
                select(SiteChannel).where(
                    SiteChannel.site_id == site_id, SiteChannel.channel_key == channel_key
                )
            )
        ).scalar_one_or_none()
        return None if row is None else SiteChannelRecord.model_validate(row)

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        channel_key: str,
        values: dict[str, Any],
    ) -> SiteChannelRecord:
        now = datetime.now(UTC)
        row = SiteChannel(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            channel_key=channel_key,
            created_at=now,
            updated_at=now,
            **values,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return SiteChannelRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, channel_id: str, values: dict[str, Any]
    ) -> SiteChannelRecord:
        row = (
            await db.execute(
                update(SiteChannel)
                .where(SiteChannel.id == channel_id)
                .values(**values, updated_at=datetime.now(UTC))
                .returning(SiteChannel)
            )
        ).scalar_one()
        await db.flush()
        return SiteChannelRecord.model_validate(row)

    async def list(self, db: AsyncSession, site_id: str) -> list[SiteChannelRecord]:
        rows = await db.execute(
            select(SiteChannel).where(SiteChannel.site_id == site_id).order_by(SiteChannel.seq)
        )
        return [SiteChannelRecord.model_validate(row) for row in rows.scalars().all()]


site_channels = SiteChannelRepository()
