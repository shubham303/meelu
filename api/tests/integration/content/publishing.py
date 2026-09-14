async def user_id_for(site: dict) -> str:
    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.sites.models.site import Site

    async with unit_of_work() as db:
        result = await db.execute(select(Site.user_id).where(Site.id == site["id"]))
        return result.scalar_one()


async def channel_enabled(site: dict, channel_key: str) -> bool:
    from src.content.channels import service as channels_service
    from src.core.database import unit_of_work

    user_id = await user_id_for(site)
    async with unit_of_work() as db:
        channel = await channels_service.get_channel(db, user_id, site["id"], channel_key)
        return channel.enabled
