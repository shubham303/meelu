from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.competitors.repository import seo_competitors
from src.seo.competitors.schemas import CompetitorRecord, CompetitorUpdateRequest

COMPETITOR_NOT_FOUND = "No such competitor on this website."


class SeoCompetitorService:
    async def list(
        self, db: AsyncSession, site_id: str, state: str | None
    ) -> list[CompetitorRecord]:
        return await seo_competitors.list(db, site_id, state)

    async def patch(
        self, db: AsyncSession, site_id: str, competitor_id: str, body: CompetitorUpdateRequest
    ) -> CompetitorRecord:
        patch = body.model_dump(exclude_none=True)
        updated = await seo_competitors.patch(db, site_id, competitor_id, patch)
        if updated is None:
            raise HTTPException(404, COMPETITOR_NOT_FOUND)
        return updated


seo_competitor_service = SeoCompetitorService()
