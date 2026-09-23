from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits import service as credits_service
from src.sites import repository as repo
from src.sites.schemas import (
    SiteCreateRequest,
    SiteFilters,
    SiteRecord,
    SiteUpdateRequest,
)


async def list_sites(
    db: AsyncSession, user_id: str, filters: SiteFilters, paging: PaginationParams
) -> PaginatedApiResponse[SiteRecord]:
    return await repo.list_sites(db, user_id, filters, paging)


async def get_site(db: AsyncSession, user_id: str, site_id: str) -> SiteRecord:
    site = await repo.get_site(db, user_id, site_id)
    if site is None:
        raise HTTPException(404, "Not found")
    return site


async def create_site(db: AsyncSession, user_id: str, body: SiteCreateRequest) -> SiteRecord:
    clash = await repo.find_site_by_domain(db, user_id, body.domain)
    if clash:
        raise HTTPException(
            409,
            f"{clash.name} ({body.domain}) is already in this workspace — switch to it rather "
            f"than adding it twice.",
        )
    site = await repo.create_site(db, user_id, body.model_dump())
    await credits_service.start_site_billing(db, user_id, site.id)
    refreshed = await repo.get_site(db, user_id, site.id)
    return refreshed or site


async def _apply(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> SiteRecord:
    if values.get("domain"):
        clash = await repo.find_site_by_domain(db, user_id, values["domain"])
        if clash and clash.id != site_id:
            raise HTTPException(
                409, f"{clash.name} already uses {values['domain']} in this workspace."
            )
    merged = await repo.merge_site(db, user_id, site_id, values)
    if merged is None:
        raise HTTPException(404, "Not found")
    return merged


async def patch_site(
    db: AsyncSession, user_id: str, site_id: str, body: SiteUpdateRequest
) -> SiteRecord:
    return await _apply(db, user_id, site_id, body.changes())


async def patch_site_as_agent(
    db: AsyncSession, user_id: str, site_id: str, body: SiteUpdateRequest
) -> SiteRecord:
    values = body.changes()
    if not values:
        raise HTTPException(400, "Nothing to save.")
    return await _apply(db, user_id, site_id, values)


async def delete_site(db: AsyncSession, user_id: str, site_id: str) -> SiteRecord:
    deleted = await repo.delete_site(db, user_id, site_id)
    if deleted is None:
        raise HTTPException(404, "Not found")
    return deleted
