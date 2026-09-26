from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.common import fields
from src.seo.competitors.schemas import CompetitorRecord, CompetitorUpdateRequest
from src.seo.competitors.service import seo_competitor_service

router = APIRouter()


@router.get("/competitors")
async def list_competitors(
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[CompetitorRecord]:
    return await seo_competitor_service.list(
        db, ctx.site_id, None if fields.blank(state) else fields.competitor_state(state)
    )


@router.patch("/competitors/{competitor_id}")
async def patch_competitor(
    competitor_id: str,
    body: CompetitorUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CompetitorRecord:
    return await seo_competitor_service.patch(db, ctx.site_id, competitor_id, body)
