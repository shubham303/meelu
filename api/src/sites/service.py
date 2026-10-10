from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits import billing
from src.credits.service import credit_service
from src.settings import settings
from src.sites.repository import sites
from src.sites.schemas import (
    SiteCreateRequest,
    SiteFilters,
    SiteRecord,
    SiteRef,
    SiteUpdateRequest,
)


class SiteService:
    async def list(
        self, db: AsyncSession, user_id: str, filters: SiteFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[SiteRecord]:
        return await sites.list(db, user_id, filters, paging)

    async def get(self, db: AsyncSession, user_id: str, site_id: str) -> SiteRecord:
        site = await sites.get(db, user_id, site_id)
        if site is None:
            raise HTTPException(404, "Not found")
        return site

    async def create(self, db: AsyncSession, user_id: str, body: SiteCreateRequest) -> SiteRecord:
        clash = await sites.find_by_domain(db, user_id, body.domain)
        if clash:
            raise HTTPException(
                409,
                f"{clash.name} ({body.domain}) is already in this workspace — switch to it rather "
                f"than adding it twice.",
            )
        site = await sites.create(db, user_id, body.model_dump())
        await credit_service.start_site_billing(db, user_id, site.id, site.domain)
        refreshed = await sites.get(db, user_id, site.id)
        return refreshed or site

    async def update(
        self, db: AsyncSession, user_id: str, site_id: str, body: SiteUpdateRequest
    ) -> SiteRecord:
        return await self._apply(db, user_id, site_id, body.changes())

    async def update_as_agent(
        self, db: AsyncSession, user_id: str, site_id: str, body: SiteUpdateRequest
    ) -> SiteRecord:
        values = body.changes()
        if not values:
            raise HTTPException(400, "Nothing to save.")
        return await self._apply(db, user_id, site_id, values)

    async def delete(self, db: AsyncSession, user_id: str, site_id: str) -> SiteRecord:
        deleted = await sites.delete(db, user_id, site_id)
        if deleted is None:
            raise HTTPException(404, "Not found")
        return deleted

    async def purge_paused(self, db: AsyncSession) -> Sequence[SiteRef]:
        before = datetime.now(UTC) - timedelta(days=settings.sites_paused_retention_days)
        return await sites.delete_paused_before(db, billing.DISABLED, before)

    async def _apply(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> SiteRecord:
        if values.get("domain"):
            clash = await sites.find_by_domain(db, user_id, values["domain"])
            if clash and clash.id != site_id:
                raise HTTPException(
                    409, f"{clash.name} already uses {values['domain']} in this workspace."
                )
        merged = await sites.merge(db, user_id, site_id, values)
        if merged is None:
            raise HTTPException(404, "Not found")
        return merged


site_service = SiteService()
