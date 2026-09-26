from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.channels.repository import site_channels
from src.content.platform_seeds import PLATFORM_SEEDS, SEEDS_BY_KEY, PlatformSeed
from src.content.schemas.channels import SiteChannelRecord, SiteChannelUpdateRequest


def _seed_values(seed: PlatformSeed) -> dict[str, Any]:
    return {"enabled": True, "rules": seed.rules()}


def _require_seed(channel_key: str) -> PlatformSeed:
    seed = SEEDS_BY_KEY.get(channel_key)
    if seed is None:
        known = ", ".join(s.key for s in PLATFORM_SEEDS)
        raise HTTPException(400, f'Unknown channel "{channel_key}". Supported: {known}.')
    return seed


class SiteChannelService:
    async def list(self, db: AsyncSession, user_id: str, site_id: str) -> list[SiteChannelRecord]:
        existing = await site_channels.list(db, site_id)
        present = {c.channel_key for c in existing}
        for seed in PLATFORM_SEEDS:
            if seed.key not in present:
                existing.append(
                    await site_channels.create(db, user_id, site_id, seed.key, _seed_values(seed))
                )
        return existing

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, channel_key: str
    ) -> SiteChannelRecord:
        seed = _require_seed(channel_key)
        channel = await site_channels.get(db, site_id, channel_key)
        if channel is None:
            channel = await site_channels.create(db, user_id, site_id, seed.key, _seed_values(seed))
        return channel

    async def require_enabled(
        self, db: AsyncSession, user_id: str, site_id: str, channel_key: str
    ) -> SiteChannelRecord:
        channel = await self.get(db, user_id, site_id, channel_key)
        if not channel.enabled:
            raise HTTPException(
                400, f"{SEEDS_BY_KEY[channel_key].label} is turned off for this site."
            )
        return channel

    async def update(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        channel_key: str,
        body: SiteChannelUpdateRequest,
    ) -> SiteChannelRecord:
        channel = await self.get(db, user_id, site_id, channel_key)
        values = body.changes()
        if not values:
            return channel
        return await site_channels.update(db, channel.id, values)

    async def reset_rules(
        self, db: AsyncSession, user_id: str, site_id: str, channel_key: str
    ) -> SiteChannelRecord:
        channel = await self.get(db, user_id, site_id, channel_key)
        return await site_channels.update(
            db, channel.id, {"rules": SEEDS_BY_KEY[channel_key].rules()}
        )


site_channel_service = SiteChannelService()
