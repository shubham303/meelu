from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.gap.schemas import GapPagesRequest, TopicPagesRequest, TopicPagesResult
from src.seo.gap.service import seo_gap_service
from src.seo.page_suggestions.schemas import CreateResult

router = APIRouter()


@router.post("/page-suggestions/propose-gaps")
async def propose_gap_pages(
    body: GapPagesRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await seo_gap_service.propose_gap_pages(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/propose-topic")
async def propose_topic_pages(
    body: TopicPagesRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> TopicPagesResult:
    return await seo_gap_service.propose_topic_pages(db, ctx.user_id, ctx.site_id, body)
