from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.channels import repository as repo
from src.content.platform_seeds import PLATFORM_SEEDS, SEEDS_BY_KEY, PlatformSeed
from src.content.schemas.channels import SiteChannelRecord, SiteChannelUpdateRequest


def seed_values(seed: PlatformSeed) -> dict[str, Any]:
    return {
        "enabled": True,
        "rules": seed.rules(),
        "timezone": "UTC",
        "posting_windows": [],
        "min_gap_hours": 0 if seed.key == "website" else 24,
    }


def require_seed(channel_key: str) -> PlatformSeed:
    seed = SEEDS_BY_KEY.get(channel_key)
    if seed is None:
        known = ", ".join(s.key for s in PLATFORM_SEEDS)
        raise HTTPException(400, f'Unknown channel "{channel_key}". Supported: {known}.')
    return seed


async def list_channels(db: AsyncSession, user_id: str, site_id: str) -> list[SiteChannelRecord]:
    existing = await repo.list_channels(db, site_id)
    present = {c.channel_key for c in existing}
    for seed in PLATFORM_SEEDS:
        if seed.key not in present:
            existing.append(
                await repo.create_channel(db, user_id, site_id, seed.key, seed_values(seed))
            )
    return existing


async def get_channel(
    db: AsyncSession, user_id: str, site_id: str, channel_key: str
) -> SiteChannelRecord:
    seed = require_seed(channel_key)
    channel = await repo.get_channel(db, site_id, channel_key)
    if channel is None:
        channel = await repo.create_channel(db, user_id, site_id, seed.key, seed_values(seed))
    return channel


async def require_enabled(
    db: AsyncSession, user_id: str, site_id: str, channel_key: str
) -> SiteChannelRecord:
    channel = await get_channel(db, user_id, site_id, channel_key)
    if not channel.enabled:
        raise HTTPException(400, f"{SEEDS_BY_KEY[channel_key].label} is turned off for this site.")
    return channel


async def sync_enabled(db: AsyncSession, user_id: str, site_id: str, connected: set[str]) -> None:
    for channel in await list_channels(db, user_id, site_id):
        if channel.channel_key == "website":
            continue
        enabled = channel.channel_key in connected
        if channel.enabled != enabled:
            await repo.update_channel(db, channel.id, {"enabled": enabled})


async def update_channel(
    db: AsyncSession, user_id: str, site_id: str, channel_key: str, body: SiteChannelUpdateRequest
) -> SiteChannelRecord:
    channel = await get_channel(db, user_id, site_id, channel_key)
    values = body.changes()
    if not values:
        return channel
    return await repo.update_channel(db, channel.id, values)


async def reset_rules(
    db: AsyncSession, user_id: str, site_id: str, channel_key: str
) -> SiteChannelRecord:
    channel = await get_channel(db, user_id, site_id, channel_key)
    return await repo.update_channel(db, channel.id, {"rules": SEEDS_BY_KEY[channel_key].rules()})
